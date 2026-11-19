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

from .const import (
    CONF_CHARGING_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_FINALIZATION,
    CONF_ODOMETER_ENTITY,
    CONF_ODOMETER_UNIT,
    CONF_PRICE,
    CONF_PRICE_ENTITY,
    CONF_PRICE_MODE,
    CONF_SOC_ENTITY,
    DOMAIN,
    FINALIZE_IMMEDIATE,
    FINALIZE_ODOMETER,
    FINALIZE_MANUAL,
    MAX_HISTORY,
    PRICE_MODE_SENSOR,
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
        for key in (CONF_SOC_ENTITY, CONF_ODOMETER_ENTITY, CONF_PRICE_ENTITY):
            if self.config.get(key):
                entities.append(self.config[key])
        self._unsub.append(
            async_track_state_change_event(self.hass, entities, self._handle_state_change)
        )

        # Reconcile the persisted session with the real charging state after restart.
        charging_state = self.hass.states.get(self.config[CONF_CHARGING_ENTITY])
        if charging_state is not None and charging_state.state not in ("unknown", "unavailable"):
            if charging_state.state == "on":
                if self.data.get("session") is None:
                    self._start_session()
                    self.data["diagnostic"] = "Carga detectada al iniciar Home Assistant"
                else:
                    self.data["session"]["status"] = "charging"
                    self.data["session"]["ended_at"] = None
                    self.data["status"] = "charging"
                    self.data["diagnostic"] = "Sesión recuperada tras reiniciar Home Assistant"
            elif charging_state.state == "off" and self.data.get("session") is not None:
                if self.data["session"].get("ended_at") is None:
                    self._stop_session()
                self._try_finalize()
            await self._async_save()

    async def _async_update_data(self):
        """Expose current state; source updates are event-driven."""
        charging = self.hass.states.get(self.config[CONF_CHARGING_ENTITY])
        if charging is None:
            raise UpdateFailed("No se encuentra la entidad de estado de carga")
        return self.data

    @callback
    def _handle_state_change(self, event) -> None:
        """Process source changes without treating unavailable as off."""
        entity_id = event.data["entity_id"]
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None or new_state.state in ("unknown", "unavailable"):
            self.data["diagnostic"] = f"Lectura no disponible: {entity_id}"
            self.async_set_updated_data(self.data)
            self.hass.async_create_task(self._async_save())
            return

        if entity_id == self.config[CONF_CHARGING_ENTITY]:
            if new_state.state == "on" and self.data.get("session") is None:
                self._start_session()
            elif (
                new_state.state == "off"
                and old_state is not None
                and old_state.state == "on"
                and self.data.get("session") is not None
            ):
                self._stop_session()

        if self.data.get("session") is not None:
            self._capture_measurements(entity_id, new_state.state)

        self._try_finalize()
        self.async_set_updated_data(self.data)
        self.hass.async_create_task(self._async_save())

    def _start_session(self) -> None:
        """Start a session with only valid available baselines."""
        now = datetime.now(timezone.utc).isoformat()
        soc = self._read_soc()
        odo = self._read_odometer()
        self.data["session"] = {
            "started_at": now,
            "ended_at": None,
            "soc_start": soc if soc is not None and 0 < soc <= 100 else None,
            "soc_max": soc if soc is not None and 0 < soc <= 100 else None,
            "soc_end": None,
            "energy_kwh": None,
            "energy_valid": False,
            "odometer_start_km": odo,
            "odometer_end_km": None,
            "price_per_kwh": self._read_session_price(),
            "price_source": self.config.get(CONF_PRICE_MODE, "manual"),
            "cost": None,
            "cost_complete": bool(self.config.get("tariff_periods")) or self._read_session_price() is not None,
            "unpriced_energy_kwh": 0.0,
            "status": "charging",
            "tariff_breakdown": {},
            "tariff_estimated": False,
            "last_energy_sample_kwh": 0.0,
            "last_energy_sample_at": now,
        }
        self.data["status"] = "charging"
        self.data["diagnostic"] = "Sesión iniciada"
        energy_entity = self.config[CONF_ENERGY_ENTITY]
        energy_state = self.hass.states.get(energy_entity)
        if energy_state is not None:
            self._capture_measurements(energy_entity, energy_state.state)

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
        if entity_id == self.config[CONF_ENERGY_ENTITY]:
            state = self.hass.states.get(entity_id)
            unit = (state.attributes.get("unit_of_measurement") or "").lower() if state else ""
            value = _number(raw_value)
            if value is not None and value >= 0 and unit in ("kwh", "wh"):
                if unit == "wh":
                    value /= 1000
                previous = session.get("last_energy_sample_kwh")
                now = dt_util.utcnow()
                previous_at = session.get("last_energy_sample_at")
                if previous is None:
                    # Defensive recovery for sessions created by an older prototype.
                    session["last_energy_sample_kwh"] = 0.0
                    session["last_energy_sample_at"] = session.get("started_at")
                    previous = 0.0
                    previous_at = session.get("last_energy_sample_at")
                if value >= previous:
                    delta = value - previous
                    if delta > 0 and previous_at:
                        self._allocate_tariff_delta(
                            session, datetime.fromisoformat(previous_at), now, delta
                        )
                    session["energy_kwh"] = round(
                        (session.get("energy_kwh") or 0.0) + delta, 4
                    )
                    session["last_energy_sample_kwh"] = value
                    session["last_energy_sample_at"] = now.isoformat()
                    session["energy_valid"] = True
                else:
                    # A counter reset is a new baseline, not negative energy.
                    session["last_energy_sample_kwh"] = value
                    session["last_energy_sample_at"] = now.isoformat()
                    self.data["diagnostic"] = "Contador reiniciado; nueva referencia establecida"
            elif value is not None:
                self.data["diagnostic"] = (
                    f"Unidad de energía no compatible: {unit or 'sin unidad'}"
                )

        if self.config.get(CONF_SOC_ENTITY) == entity_id:
            state = self.hass.states.get(entity_id)
            unit = (state.attributes.get("unit_of_measurement") or "").lower() if state else ""
            value = _number(raw_value)
            if unit == "%" and value is not None and 0 < value <= 100:
                previous = session.get("soc_max")
                if previous is None or value > previous:
                    session["soc_max"] = value

        if self.config.get(CONF_ODOMETER_ENTITY) == entity_id:
            value = self._read_odometer()
            if value is not None:
                session["odometer_last_km"] = value


    def _allocate_tariff_delta(self, session, start_utc, end_utc, energy_delta):
        """Allocate a sampled energy increment across configured local tariff periods."""
        periods = self.config.get("tariff_periods") or []
        if not periods:
            price = session.get("price_per_kwh")
            if price is not None:
                bucket = session.setdefault("tariff_breakdown", {}).setdefault(
                    "Precio fijo", {"energy_kwh": 0.0, "cost": 0.0, "price_per_kwh": price}
                )
                bucket["energy_kwh"] += energy_delta
                bucket["cost"] += energy_delta * price
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
            allocation = allocate_energy_by_time(
                dt_util.as_local(start_utc), dt_util.as_local(end_utc),
                energy_delta, periods
            )
        except ValueError as err:
            session["cost_complete"] = False
            session["unpriced_energy_kwh"] = round(
                session.get("unpriced_energy_kwh", 0.0) + energy_delta, 6
            )
            self.data["diagnostic"] = str(err)
            return
        session["tariff_estimated"] = True
        buckets = session.setdefault("tariff_breakdown", {})
        for item in allocation["breakdown"]:
            bucket = buckets.setdefault(item["period"], {
                "energy_kwh": 0.0, "cost": 0.0,
                "price_per_kwh": item["price_per_kwh"]
            })
            bucket["energy_kwh"] += item["energy_kwh"]
            bucket["cost"] += item["cost"]

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
        value = _number(state.state)
        return value if value is not None and 0 < value <= 100 else None

    def _read_session_price(self) -> float | None:
        """Snapshot the configured electricity price at session start."""
        if self.config.get(CONF_PRICE_MODE) == PRICE_MODE_SENSOR:
            entity_id = self.config.get(CONF_PRICE_ENTITY)
            state = self.hass.states.get(entity_id) if entity_id else None
            if state is None:
                return None
            unit = (state.attributes.get("unit_of_measurement") or "").strip().lower()
            if unit not in ("€/kwh", "eur/kwh", "eur / kwh"):
                return None
            value = _number(state.state)
            return value if value is not None and value >= 0 else None
        value = _number(str(self.config.get(CONF_PRICE, 0.0)))
        return value if value is not None and value >= 0 else None

    def _read_odometer(self) -> float | None:
        value = self._read_number(CONF_ODOMETER_ENTITY)
        if value is None:
            return None
        state = self.hass.states.get(self.config[CONF_ODOMETER_ENTITY])
        unit = (state.attributes.get("unit_of_measurement") or "").lower()
        configured = self.config.get(CONF_ODOMETER_UNIT, "km")
        if unit in ("mi", "mile", "miles") or configured == "mi":
            return value * 1.609344
        return value

    def _try_finalize(self) -> None:
        """Finalize once, using the configured strategy."""
        session = self.data.get("session")
        if session is None or session.get("ended_at") is None:
            return
        strategy = self.config.get(CONF_FINALIZATION, FINALIZE_ODOMETER)
        if strategy == FINALIZE_IMMEDIATE:
            if session.get("energy_valid"):
                self._finalize()
            else:
                self.data["diagnostic"] = "Carga detenida; falta una lectura válida de energía"
            return
        if strategy == FINALIZE_MANUAL:
            self.data["diagnostic"] = "Carga pendiente de confirmación manual"
            return
        if strategy == FINALIZE_ODOMETER:
            current = self._read_odometer()
            start = session.get("odometer_start_km")
            if current is not None and start is not None and current > start:
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
        if session.get("soc_max") is not None:
            session["soc_end"] = session["soc_max"]
        price = session.get("price_per_kwh")
        energy = session.get("energy_kwh")
        buckets = session.get("tariff_breakdown") or {}
        if buckets:
            session["cost"] = (
                round(sum(item["cost"] for item in buckets.values()), 2)
                if session.get("cost_complete", True)
                else None
            )
            session["tariff_breakdown"] = {
                name: {
                    **item,
                    "energy_kwh": round(item["energy_kwh"], 4),
                    "cost": round(item["cost"], 4),
                }
                for name, item in buckets.items()
            }
        else:
            session["cost"] = (
                round(energy * price, 2)
                if energy is not None and price is not None and session.get("cost_complete", True)
                else None
            )
        session["status"] = "completed"
        session["completed_at"] = datetime.now(timezone.utc).isoformat()
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
        if session is None or session.get("ended_at") is None or not session.get("energy_valid"):
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
        for unsub in self._unsub:
            unsub()
        await self._async_save()
