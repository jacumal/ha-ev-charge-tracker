"""Session coordinator and persistent state machine."""

from __future__ import annotations

from datetime import datetime, timezone
from homeassistant.util import dt as dt_util
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .tariff import allocate_energy_by_time, validate_periods
from .power import allocate_energy_by_power, allocate_energy_by_dynamic_price
from .units import convert_unit, normalize_currency_code

from .const import (
    CONF_CHARGING_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_ENERGY_MODE,
    CONF_FINALIZATION,
    CONF_ODOMETER_ENTITY,
    CONF_ODOMETER_UNIT,
    CONF_PRICE,
    CONF_PRICE_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PRICE_MODE,
    CONF_SOC_ENTITY,
    DOMAIN,
    ENERGY_MODE_CUMULATIVE,
    FINALIZE_IMMEDIATE,
    FINALIZE_ODOMETER,
    FINALIZE_MANUAL,
    MAX_HISTORY,
    PRICE_MODE_SENSOR,
    CONF_CURRENCY,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _number(value: str | None) -> float | None:
    """Parse a finite numeric state."""
    if value in (None, "", "unknown", "unavailable", "none"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _normalize_energy(value: str | float | None, unit: str) -> float | None:
    """Normalize a valid Wh/kWh sensor reading to kWh."""
    number = _number(str(value)) if value is not None else None
    if number is None or number < 0:
        return None
    try:
        return convert_unit(number, "energy", unit, "kWh")
    except ValueError:
        return None


def _energy_delta(previous: float | None, current: float) -> float | None:
    """Return a non-negative counter increase; None signals a reset/new baseline."""
    if previous is None or current < previous:
        return None
    return current - previous


def _state_is_fresh(state, now: datetime, max_age_seconds: int = 600) -> bool:
    """Return whether a Home Assistant state has a recent observation timestamp."""
    if state is None or state.state in ("unknown", "unavailable"):
        return False
    updated = getattr(state, "last_updated", None)
    if updated is None:
        return False
    age = (now - updated).total_seconds()
    return 0 <= age <= max_age_seconds


def _state_updated_at_or_after(state, moment: datetime) -> bool:
    """Return whether a state was observed at or after a lifecycle boundary."""
    updated = getattr(state, "last_updated", None)
    if updated is None:
        return False
    if updated.tzinfo is None and moment.tzinfo is not None:
        updated = updated.replace(tzinfo=moment.tzinfo)
    elif updated.tzinfo is not None and moment.tzinfo is None:
        moment = moment.replace(tzinfo=updated.tzinfo)
    return updated >= moment


def _session_recovery_action(charging_state: str | None, session: dict | None) -> str:
    """Classify a charger observation against the persisted session lifecycle."""
    if charging_state not in ("on", "off"):
        return "preserve"
    if charging_state == "on":
        if session is None:
            return "start"
        return "resume" if session.get("ended_at") is not None else "continue"
    if session is not None and session.get("ended_at") is None:
        return "stop"
    return "idle"

def _normalize_odometer(value: float | None, sensor_unit: str, configured_unit: str = "km") -> float | None:
    """Normalize odometer readings to km, preferring an explicit HA unit.

    The configured unit is a fallback for sensors that do not publish a unit.
    """
    if value is None or value < 0:
        return None
    unit = (sensor_unit or "").strip()
    if unit:
        try:
            return convert_unit(value, "distance", unit, "km")
        except ValueError:
            return None
    try:
        return convert_unit(value, "distance", configured_unit or "km", "km")
    except ValueError:
        return None


class EVChargeCoordinator(DataUpdateCoordinator):
    """Track one configured vehicle/charger profile."""

    def __init__(self, hass: HomeAssistant, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.config = {**entry.data, **entry.options}
        self.store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}")
        self._unsub = []
        self.data = {
            "status": "idle",
            "session": None,
            "latest": None,
            "history": [],
            "diagnostic": "Esperando una nueva carga",
        }

    async def async_setup(self) -> None:
        """Restore saved state and subscribe to source entities."""
        saved = await self.store.async_load()
        if isinstance(saved, dict):
            self.data.update(saved)
        entities = [
            self.config[CONF_CHARGING_ENTITY],
            self.config[CONF_ENERGY_ENTITY],
        ]
        for period in self.config.get("tariff_periods", []):
            if period.get("price_entity"):
                entities.append(period["price_entity"])
        for key in (CONF_SOC_ENTITY, CONF_ODOMETER_ENTITY, CONF_PRICE_ENTITY, CONF_POWER_ENTITY):
            if self.config.get(key):
                entities.append(self.config[key])
        self._unsub.append(
            async_track_state_change_event(self.hass, entities, self._handle_state_change)
        )

        # Reconcile persisted state only when the charger reports a definitive state.
        had_restored_session = self.data.get("session") is not None
        charging_state = self.hass.states.get(self.config[CONF_CHARGING_ENTITY])
        action = _session_recovery_action(
            charging_state.state if charging_state is not None else None,
            self.data.get("session"),
        )
        if action == "start":
            self._start_session()
            self.data["diagnostic"] = "Carga detectada al iniciar Home Assistant"
        elif action == "resume":
            self.data["session"]["status"] = "charging"
            self.data["session"]["ended_at"] = None
            self.data["status"] = "charging"
            self.data["diagnostic"] = "Sesión recuperada tras reiniciar Home Assistant"
        elif action == "stop":
            self._stop_session()
            self._try_finalize()
        if action != "preserve":
            if had_restored_session and self.data.get("session") is not None:
                # A restart is a new observation point: do not carry a pre-restart
                # dynamic price forward if its source is now unavailable.
                self._capture_initial_tariff_prices(
                    self.data["session"], dt_util.utcnow().isoformat()
                )
            await self._async_save()

    async def _async_update_data(self):
        """Expose current state and retry eligible session finalization."""
        charging = self.hass.states.get(self.config[CONF_CHARGING_ENTITY])
        if charging is None:
            raise UpdateFailed("No se encuentra la entidad de estado de carga")
        previous_session = self.data.get("session")
        self._try_finalize()
        if previous_session is not None and self.data.get("session") is None:
            await self._async_save()
        return self.data

    @callback
    def _handle_state_change(self, event) -> None:
        """Process source changes without treating unavailable as off."""
        entity_id = event.data["entity_id"]
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unknown", "unavailable"):
            if self.data.get("session") is not None and self._is_tariff_price_entity(entity_id):
                self._append_tariff_price_sample(entity_id, None)
            self.data["diagnostic"] = f"Lectura no disponible: {entity_id}"
            self.async_set_updated_data(self.data)
            self.hass.async_create_task(self._async_save())
            return

        if entity_id == self.config[CONF_CHARGING_ENTITY]:
            action = _session_recovery_action(new_state.state, self.data.get("session"))
            if action == "start":
                self._start_session()
            elif action == "resume":
                # A brief OFF/ON transition resumes the pending session.
                self.data["session"]["ended_at"] = None
                self.data["session"]["status"] = "charging"
                self.data["status"] = "charging"
                self.data["diagnostic"] = "Carga reanudada; se conserva la sesión"
            elif action == "stop":
                # Also reconcile unknown/unavailable -> OFF after a restart.
                self._stop_session()

        if self.data.get("session") is not None:
            if self._is_tariff_price_entity(entity_id):
                self._append_tariff_price_sample(entity_id)
            self._capture_measurements(entity_id, new_state.state)

        self._try_finalize()
        self.async_set_updated_data(self.data)
        self.hass.async_create_task(self._async_save())

    def _start_session(self) -> None:
        """Start a session with only valid available baselines."""
        now = datetime.now(timezone.utc).isoformat()
        soc = self._read_soc()
        odo = self._read_odometer()
        energy_reading = self._read_energy_kwh()
        energy_baseline = (
            energy_reading
            if self.config.get(CONF_ENERGY_MODE) == ENERGY_MODE_CUMULATIVE
            else 0.0
        )
        self.data["session"] = {
            "started_at": now,
            "ended_at": None,
            "soc_start": soc if soc is not None and 0 < soc <= 100 else None,
            "soc_max": soc if soc is not None and 0 < soc <= 100 else None,
            "soc_last": None,
            "soc_last_at": None,
            "soc_end": None,
            "energy_kwh": 0.0,
            "energy_valid": False,
            "energy_baseline_kwh": energy_baseline,
            "odometer_start_km": odo,
            "odometer_end_km": None,
            "price_per_kwh": self._read_session_price(),
            "price_source": self.config.get(CONF_PRICE_MODE, "manual"),
            "currency": self._currency_code(),
            "cost": None,
            "cost_complete": bool(self.config.get("tariff_periods")) or self._read_session_price() is not None,
            "unpriced_energy_kwh": 0.0,
            "priced_energy_kwh": 0.0,
            "known_cost": None,
            "status": "charging",
            "tariff_breakdown": {},
            "tariff_estimated": False,
            # The session counter's first valid observation is its baseline.
            # Never assume zero when the source was stale/unavailable at start.
            "last_energy_sample_kwh": energy_reading,
            "last_energy_sample_at": now if energy_reading is not None else None,
            "power_samples": [],
            "price_samples": [],
        }
        self._capture_initial_tariff_prices(self.data["session"], now)
        self.data["status"] = "charging"
        self.data["diagnostic"] = "Sesión iniciada"
        initial_power = self._read_power_kw()
        if initial_power is not None:
            self.data["session"]["power_samples"].append({"at": now, "power_kw": initial_power})
        if (
            self.config.get(CONF_ENERGY_MODE) != ENERGY_MODE_CUMULATIVE
            and energy_reading is not None
        ):
            self._capture_measurements(
                self.config[CONF_ENERGY_ENTITY],
                str(energy_reading * 1000 if self._energy_unit_is_wh() else energy_reading),
            )

    def _energy_unit_is_wh(self) -> bool:
        """Return whether the configured energy sensor reports Wh."""
        entity_id = self.config.get(CONF_ENERGY_ENTITY)
        state = self.hass.states.get(entity_id) if entity_id else None
        return bool(
            state
            and (state.attributes.get("unit_of_measurement") or "").strip().lower() == "wh"
        )

    def _stop_session(self) -> None:
        """Mark session ended; do not finalize until configured criteria pass."""
        session = self.data["session"]
        session["ended_at"] = datetime.now(timezone.utc).isoformat()
        session["status"] = "pending_finalization"
        self.data["status"] = "pending_finalization"
        self.data["diagnostic"] = "Carga terminada; pendiente de consolidación"

    def _capture_measurements(self, entity_id: str, raw_value: str) -> None:
        """Update energy, SOC maximum and odometer readings."""
        session = self.data["session"]
        if self.config.get(CONF_POWER_ENTITY) == entity_id:
            power = self._read_power_kw()
            if power is not None:
                samples = session.setdefault("power_samples", [])
                samples.append({"at": dt_util.utcnow().isoformat(), "power_kw": power})
                if len(samples) > 2000:
                    session["power_samples"] = samples[-2000:]

        if entity_id == self.config[CONF_ENERGY_ENTITY]:
            value = self._read_energy_kwh()
            if value is not None:
                previous = session.get("last_energy_sample_kwh")
                now = dt_util.utcnow()
                previous_at = session.get("last_energy_sample_at")
                if previous is None:
                    # First valid sample establishes a baseline; it is never counted retroactively.
                    session["last_energy_sample_kwh"] = value
                    session["last_energy_sample_at"] = now.isoformat()
                    session["energy_baseline_kwh"] = value
                    self.data["diagnostic"] = "Referencia inicial de energía establecida"
                elif (delta := _energy_delta(previous, value)) is not None:
                    if delta > 0 and previous_at:
                        self._allocate_tariff_delta(
                            session, datetime.fromisoformat(previous_at), now, delta
                        )
                        # Preserve only the latest sample as the next interval's
                        # starting reference; the previous profile is now consumed.
                        samples = session.get("power_samples", [])
                        eligible = [
                            item for item in samples
                            if datetime.fromisoformat(item["at"]) <= now
                        ]
                        session["power_samples"] = eligible[-1:] if eligible else []
                    session["energy_kwh"] = round(
                        (session.get("energy_kwh") or 0.0) + delta, 4
                    )
                    session["last_energy_sample_kwh"] = value
                    session["last_energy_sample_at"] = now.isoformat()
                    if delta > 0:
                        session["energy_valid"] = True
                else:
                    # A reset/rollover is a new baseline, never negative delivered energy.
                    session["last_energy_sample_kwh"] = value
                    session["last_energy_sample_at"] = now.isoformat()
                    self.data["diagnostic"] = "Contador reiniciado; nueva referencia establecida"
            else:
                state = self.hass.states.get(entity_id)
                if state is not None and state.state not in ("unknown", "unavailable"):
                    unit = (state.attributes.get("unit_of_measurement") or "").lower()
                    self.data["diagnostic"] = (
                        f"Unidad de energía no compatible: {unit or 'sin unidad'}"
                    )

        if self.config.get(CONF_SOC_ENTITY) == entity_id:
            state = self.hass.states.get(entity_id)
            unit = (state.attributes.get("unit_of_measurement") or "").lower() if state else ""
            value = _number(raw_value)
            if unit == "%" and value is not None and 0 < value <= 100:
                session["soc_last"] = value
                session["soc_last_at"] = dt_util.utcnow().isoformat()
                previous = session.get("soc_max")
                if previous is None or value > previous:
                    session["soc_max"] = value

        if self.config.get(CONF_ODOMETER_ENTITY) == entity_id:
            value = self._read_odometer()
            if value is not None:
                session["odometer_last_km"] = value


    def _allocate_tariff_delta(self, session, start_utc, end_utc, energy_delta):
        """Allocate energy using tariff periods and the price valid in each interval."""
        periods = self.config.get("tariff_periods") or []
        if not periods:
            price = session.get("price_per_kwh")
            if price is not None:
                bucket = session.setdefault("tariff_breakdown", {}).setdefault(
                    "Precio fijo", {"energy_kwh": 0.0, "cost": 0.0, "price_per_kwh": price}
                )
                bucket["energy_kwh"] += energy_delta
                bucket["cost"] += energy_delta * price
                session["priced_energy_kwh"] = round(session.get("priced_energy_kwh", 0.0) + energy_delta, 6)
            else:
                session["cost_complete"] = False
                session["unpriced_energy_kwh"] = round(
                    session.get("unpriced_energy_kwh", 0.0) + energy_delta, 6
                )
            return
        if validate_periods(periods):
            session["cost_complete"] = False
            session["unpriced_energy_kwh"] = round(
                session.get("unpriced_energy_kwh", 0.0) + energy_delta, 6
            )
            self.data["diagnostic"] = "Tarifas no válidas: tramo no contabilizado"
            return
        try:
            start_local = dt_util.as_local(start_utc)
            end_local = dt_util.as_local(end_utc)
            allocation = allocate_energy_by_dynamic_price(
                start_local,
                end_local,
                energy_delta,
                periods,
                session.get("power_samples") or [],
                session.get("price_samples") or [],
            )
        except ValueError as err:
            session["cost_complete"] = False
            session["unpriced_energy_kwh"] = round(
                session.get("unpriced_energy_kwh", 0.0) + energy_delta, 6
            )
            self.data["diagnostic"] = str(err)
            return

        session["tariff_estimated"] = True
        session["tariff_allocation_method"] = allocation["method"]
        session["priced_energy_kwh"] = round(
            session.get("priced_energy_kwh", 0.0) + allocation["priced_energy_kwh"], 6
        )
        session["unpriced_energy_kwh"] = round(
            session.get("unpriced_energy_kwh", 0.0) + allocation["unpriced_energy_kwh"], 6
        )
        if allocation["unpriced_energy_kwh"] > 0:
            session["cost_complete"] = False
            self.data["diagnostic"] = "Precio dinámico no disponible para parte de la energía"
        buckets = session.setdefault("tariff_breakdown", {})
        for item in allocation["breakdown"]:
            bucket = buckets.setdefault(item["period"], {
                "energy_kwh": 0.0,
                "cost": 0.0,
                "priced_energy_kwh": 0.0,
                "unpriced_energy_kwh": 0.0,
                "price_per_kwh": item.get("price_per_kwh"),
                "price_segments": [],
            })
            bucket["energy_kwh"] = round(bucket.get("energy_kwh", 0.0) + item["energy_kwh"], 6)
            bucket["cost"] = round(bucket.get("cost", 0.0) + item["cost"], 6)
            bucket["priced_energy_kwh"] = round(
                bucket.get("priced_energy_kwh", 0.0) + item["priced_energy_kwh"], 6
            )
            bucket["unpriced_energy_kwh"] = round(
                bucket.get("unpriced_energy_kwh", 0.0) + item["unpriced_energy_kwh"], 6
            )
            for segment in item.get("price_segments", []):
                bucket.setdefault("price_segments", []).append(segment)
            prices = {segment["price_per_kwh"] for segment in bucket["price_segments"]}
            bucket["price_per_kwh"] = next(iter(prices)) if len(prices) == 1 else None

    def _is_tariff_price_entity(self, entity_id: str) -> bool:
        """Return whether an entity supplies a configured tariff-period price."""
        return any(
            period.get("price_entity") == entity_id
            for period in self.config.get("tariff_periods", [])
        )

    def _read_tariff_price(self, entity_id: str) -> float | None:
        """Read a non-negative price sensor with an explicit profile currency unit."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        unit = "".join(
            (state.attributes.get("unit_of_measurement") or "").lower().split()
        )
        currency = self._currency_code()
        accepted = {f"{currency.lower()}/kwh", f"{currency.lower()}kwh-1"}
        if currency == "EUR":
            accepted.update(("€/kwh", "eur/kwh", "eurkwh-1"))
        value = _number(state.state)
        return value if unit in accepted and value is not None and value >= 0 else None

    def _capture_initial_tariff_prices(self, session, timestamp: str) -> None:
        """Snapshot the initial value (or unavailable state) of every dynamic period."""
        for period in self.config.get("tariff_periods", []):
            entity_id = period.get("price_entity")
            if entity_id:
                session.setdefault("price_samples", []).append({
                    "at": timestamp,
                    "period": str(period["name"]),
                    "price": self._read_tariff_price(entity_id),
                })

    def _append_tariff_price_sample(self, entity_id: str, value=None) -> None:
        """Persist a timestamped price change for the matching tariff period."""
        session = self.data.get("session")
        if session is None:
            return
        price = self._read_tariff_price(entity_id) if value is None else value
        timestamp = dt_util.utcnow().isoformat()
        for period in self.config.get("tariff_periods", []):
            if period.get("price_entity") == entity_id:
                samples = session.setdefault("price_samples", [])
                samples.append({
                    "at": timestamp,
                    "period": str(period["name"]),
                    "price": price,
                })
                if len(samples) > 5000:
                    session["price_samples"] = samples[-5000:]
    def _read_power_kw(self) -> float | None:
        """Read and normalize an optional instantaneous power sensor to kW."""
        entity_id = self.config.get(CONF_POWER_ENTITY)
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None:
            return None
        value = _number(state.state)
        if value is None or value < 0:
            return None
        unit = state.attributes.get("unit_of_measurement") or ""
        try:
            return convert_unit(value, "power", unit, "kW")
        except ValueError:
            return None

    def _read_energy_kwh(self) -> float | None:
        """Read the configured energy counter and normalize Wh/kWh to kWh."""
        entity_id = self.config.get(CONF_ENERGY_ENTITY)
        state = self.hass.states.get(entity_id) if entity_id else None
        if not _state_is_fresh(state, dt_util.utcnow()):
            return None
        unit = state.attributes.get("unit_of_measurement") or ""
        return _normalize_energy(state.state, unit)

    def _read_number(self, config_key: str) -> float | None:
        entity_id = self.config.get(config_key)
        state = self.hass.states.get(entity_id) if entity_id else None
        return _number(state.state) if state else None

    def _read_soc(self) -> float | None:
        """Read SOC only when the source explicitly reports percent."""
        entity_id = self.config.get(CONF_SOC_ENTITY)
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None or (state.attributes.get("unit_of_measurement") or "").strip() != "%":
            return None
        # A sleeping vehicle can leave a plausible but obsolete SOC in HA.
        if not _state_is_fresh(state, dt_util.utcnow()):
            return None
        value = _number(state.state)
        return value if value is not None and 0 < value <= 100 else None

    def _currency_code(self) -> str:
        """Return the profile's three-letter currency code."""
        try:
            return normalize_currency_code(self.config.get(CONF_CURRENCY, "EUR"))
        except ValueError:
            return "EUR"

    def _read_session_price(self) -> float | None:
        """Snapshot the configured electricity price at session start."""
        if self.config.get(CONF_PRICE_MODE) == PRICE_MODE_SENSOR:
            entity_id = self.config.get(CONF_PRICE_ENTITY)
            state = self.hass.states.get(entity_id) if entity_id else None
            if state is None:
                return None
            unit = "".join(
                (state.attributes.get("unit_of_measurement") or "").lower().split()
            )
            currency = self._currency_code()
            accepted_units = {f"{currency.lower()}/kwh", f"{currency.lower()}kwh-1"}
            if currency == "EUR":
                accepted_units.update(("€/kwh", "eur/kwh", "eurkwh-1"))
            if unit not in accepted_units:
                return None
            value = _number(state.state)
            return value if value is not None and value >= 0 else None
        value = _number(str(self.config.get(CONF_PRICE, 0.0)))
        return value if value is not None and value >= 0 else None

    def _read_odometer(self) -> float | None:
        entity_id = self.config.get(CONF_ODOMETER_ENTITY)
        state = self.hass.states.get(entity_id) if entity_id else None
        if not _state_is_fresh(state, dt_util.utcnow()):
            return None
        value = _number(state.state)
        if value is None:
            return None
        unit = state.attributes.get("unit_of_measurement") or ""
        configured = self.config.get(CONF_ODOMETER_UNIT, "km")
        return _normalize_odometer(value, unit, configured)

    def _try_finalize(self) -> None:
        """Finalize once, using the configured strategy."""
        session = self.data.get("session")
        if session is None or session.get("ended_at") is None:
            return
        charging_state = self.hass.states.get(self.config[CONF_CHARGING_ENTITY])
        # Never finalize from a stale persisted OFF, or while charging state is
        # unknown/unavailable/on. Recovery must first establish an explicit OFF.
        if charging_state is None or charging_state.state != "off":
            return
        strategy = self.config.get(CONF_FINALIZATION, FINALIZE_ODOMETER)
        if strategy == FINALIZE_IMMEDIATE:
            # Keep the session open briefly after OFF: some chargers publish their
            # final energy counter (and the vehicle its final SOC) asynchronously.
            ended_at = datetime.fromisoformat(session["ended_at"])
            elapsed = (dt_util.utcnow() - ended_at).total_seconds()
            if elapsed < 60:
                self.data["diagnostic"] = (
                    "Carga detenida; esperando lecturas finales "
                    f"({max(0, int(60 - elapsed))} s)"
                )
                return
            if session.get("energy_valid"):
                self._finalize()
            else:
                self.data["diagnostic"] = (
                    "Carga detenida; no se recibió una lectura válida de energía "
                    "durante el margen de consolidación"
                )
            return
        if strategy == FINALIZE_MANUAL:
            self.data["diagnostic"] = "Carga pendiente de confirmación manual"
            return
        if strategy == FINALIZE_ODOMETER:
            odometer_entity = self.config.get(CONF_ODOMETER_ENTITY)
            odometer_state = self.hass.states.get(odometer_entity) if odometer_entity else None
            ended_at = datetime.fromisoformat(session["ended_at"])
            current = self._read_odometer()
            start = session.get("odometer_start_km")
            if (
                current is not None
                and start is not None
                and current > start
                and _state_updated_at_or_after(odometer_state, ended_at)
            ):
                if session.get("energy_valid"):
                    session["odometer_end_km"] = current
                    self._finalize()
                else:
                    self.data["diagnostic"] = "Odómetro aumentado; falta una lectura válida de energía"

    def _finalize(self) -> None:
        """Commit an immutable summary to history."""
        session = self.data.get("session")
        if session is None:
            return
        # Keep the last SOC only if it was refreshed close to charge completion.
        # A parked/sleeping vehicle can otherwise leave a plausible stale value.
        soc_last_at = session.get("soc_last_at")
        ended_at = session.get("ended_at")
        soc_end = None
        if soc_last_at and ended_at:
            try:
                soc_age = (
                    datetime.fromisoformat(ended_at)
                    - datetime.fromisoformat(soc_last_at)
                ).total_seconds()
                # Allow a delayed vehicle update during the post-charge grace
                # period, but reject readings that are more than 10 minutes
                # away from the actual charging stop in either direction.
                if abs(soc_age) <= 600:
                    soc_end = session.get("soc_last")
            except (TypeError, ValueError):
                pass
        session["soc_end"] = soc_end
        price = session.get("price_per_kwh")
        energy = session.get("energy_kwh")
        buckets = session.get("tariff_breakdown") or {}
        known_cost = None
        if buckets:
            known_cost = round(sum(item["cost"] for item in buckets.values()), 4)
            session["tariff_breakdown"] = {
                name: {
                    **item,
                    "energy_kwh": round(item["energy_kwh"], 4),
                    "cost": round(item["cost"], 4),
                }
                for name, item in buckets.items()
            }
        elif session.get("energy_valid") and energy is not None and price is not None:
            known_cost = round(energy * price, 4)
            session["priced_energy_kwh"] = energy
        session["known_cost"] = known_cost
        complete = bool(
            session.get("cost_complete", True)
            and session.get("energy_valid")
            and energy is not None
            and session.get("priced_energy_kwh", 0.0) >= energy - 0.0001
        )
        session["cost"] = round(known_cost, 2) if complete and known_cost is not None else None
        session["cost_status"] = "complete" if complete else (
            "partial" if known_cost is not None else "unknown"
        )
        session["status"] = "completed"
        session["completed_at"] = datetime.now(timezone.utc).isoformat()
        # Raw telemetry is only needed while allocating the active session.
        # Keep the compact tariff result, not thousands of power samples, in history.
        session.pop("power_samples", None)
        session.pop("price_samples", None)
        record = dict(session)
        record["session_id"] = record["started_at"]
        self.data["latest"] = record
        self.data["history"] = ([record] + self.data.get("history", []))[:MAX_HISTORY]
        self.data["session"] = None
        self.data["status"] = "idle"
        self.data["diagnostic"] = "Última carga consolidada"

    async def async_manual_finalize(self) -> bool:
        """Finalize a stopped session after explicit user confirmation."""
        session = self.data.get("session")
        if session is None or session.get("ended_at") is None:
            return False
        self._finalize()
        self.async_set_updated_data(self.data)
        await self._async_save()
        return True

    async def _async_save(self) -> None:
        """Persist state and history."""
        await self.store.async_save(self.data)

    async def async_shutdown(self) -> None:
        """Remove listeners and persist final state."""
        unsubscribers, self._unsub = self._unsub, []
        for unsub in unsubscribers:
            try:
                unsub()
            except ValueError:
                # Home Assistant may already have removed the listener while
                # unloading/reloading the config entry. Shutdown must remain
                # idempotent and continue cleaning up the remaining listeners.
                _LOGGER.debug("Listener was already removed during coordinator shutdown")
        await self._async_save()
