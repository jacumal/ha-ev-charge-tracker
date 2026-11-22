"""Config flow for EV Charge Tracker."""

from __future__ import annotations

import voluptuous as vol
from voluptuous import All, Coerce, Range

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .tariff import default_periods, validate_periods
from .profile_registry import build_profile_identity, find_resource_conflicts

from .const import (
    CONF_CHARGER_NAME,
    CONF_CHARGING_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_POWER_ENTITY,
    CONF_ENERGY_MODE,
    CONF_FINALIZATION,
    CONF_ODOMETER_ENTITY,
    CONF_ODOMETER_UNIT,
    CONF_PRICE,
    CONF_PRICE_ENTITY,
    CONF_PRICE_MODE,
    CONF_SOC_ENTITY,
    CONF_VEHICLE_NAME,
    DOMAIN,
    ENERGY_MODE_SESSION,
    ENERGY_MODE_CUMULATIVE,
    FINALIZE_IMMEDIATE,
    FINALIZE_ODOMETER,
    FINALIZE_MANUAL,
    PRICE_MODE_MANUAL,
    PRICE_MODE_SENSOR,
    CONF_TARIFF_PERIODS,
    CONF_TARIFF_COUNT,
    CONF_UNIT_ENERGY, CONF_UNIT_DISTANCE, CONF_UNIT_POWER, CONF_UNIT_VOLTAGE,
    CONF_UNIT_CURRENT, CONF_UNIT_TEMPERATURE, CONF_UNIT_CONSUMPTION, CONF_CURRENCY,
)


class EVChargeTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one vehicle + charger profile."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EVChargeTrackerOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Collect entity mappings for one charging profile."""
        errors = {}

        if user_input is not None:
            vehicle_name = user_input[CONF_VEHICLE_NAME].strip()
            charger_name = user_input[CONF_CHARGER_NAME].strip()
            if not vehicle_name or not charger_name:
                errors["base"] = "name_required"
            elif user_input[CONF_FINALIZATION] == FINALIZE_ODOMETER and not user_input.get(CONF_ODOMETER_ENTITY):
                errors["base"] = "odometer_required"
            elif user_input[CONF_PRICE_MODE] == PRICE_MODE_SENSOR and not user_input.get(CONF_PRICE_ENTITY):
                errors["base"] = "price_sensor_required"
            else:
                try:
                    identity = build_profile_identity(vehicle_name, charger_name)
                except ValueError:
                    errors["base"] = "name_required"
                else:
                    conflicts = find_resource_conflicts(
                        user_input,
                        (
                            {**entry.data, **entry.options}
                            for entry in self.hass.config_entries.async_entries(DOMAIN)
                        ),
                    )
                    if conflicts:
                        errors["base"] = "resource_conflict"
                    else:
                        await self.async_set_unique_id(
                            f"{identity['vehicle_id']}__{identity['charger_id']}"
                        )
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=f"{vehicle_name} · {charger_name}",
                            data={**user_input, **identity},
                        )

        schema = vol.Schema(
            {
                vol.Required(CONF_VEHICLE_NAME): str,
                vol.Required(CONF_CHARGER_NAME): str,
                vol.Required(CONF_CHARGING_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Required(CONF_ENERGY_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_ENERGY_MODE, default=ENERGY_MODE_SESSION): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": ENERGY_MODE_SESSION, "label": "Energía de la sesión (se reinicia en cada carga)"},
                            {"value": ENERGY_MODE_CUMULATIVE, "label": "Contador acumulativo (lectura total que nunca se reinicia)"}
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_SOC_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ODOMETER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ODOMETER_UNIT, default="km"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "km", "label": "Kilómetros"},
                            {"value": "mi", "label": "Millas"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(CONF_PRICE_MODE, default=PRICE_MODE_MANUAL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": PRICE_MODE_MANUAL, "label": "Precio manual fijo"},
                            {"value": PRICE_MODE_SENSOR, "label": "Precio desde sensor de Home Assistant"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_PRICE, default=0.11): All(Coerce(float), Range(min=0)),
                vol.Optional(CONF_PRICE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_FINALIZATION, default=FINALIZE_ODOMETER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": FINALIZE_ODOMETER, "label": "Cuando aumente el odómetro"},
                            {"value": FINALIZE_IMMEDIATE, "label": "Al terminar la carga"},
                            {"value": FINALIZE_MANUAL, "label": "Confirmación manual desde un botón"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "charging_help": "binary_sensor: on = cargando; off = no cargando. unknown/unavailable no finalizan una sesión.",
                "energy_help": "sensor en kWh o Wh. Debe representar la energía entregada en la sesión actual.",
                "soc_help": "sensor en %. Es opcional; si falta, los datos de batería quedarán pendientes.",
                "odometer_help": "sensor en km o mi. Necesario para finalizar usando el criterio de aumento del odómetro.",
                "price_help": "Elige un precio manual fijo o un sensor numérico en €/kWh. Se guarda el precio observado al iniciar cada sesión para conservar el coste histórico.",
            },
        )



class EVChargeTrackerOptionsFlow(config_entries.OptionsFlow):
    """Edit profile mappings and tariff periods without losing session history."""

    def __init__(self):
        self._period_count = 1
        self._period_index = 0
        self._period_drafts = []

    async def async_step_init(self, user_input=None):
        """Choose which profile settings to edit."""
        if user_input is not None:
            if user_input["section"] == "profile":
                return await self.async_step_profile()
            if user_input["section"] == "tariffs":
                return await self.async_step_tariffs()
            return await self.async_step_units()
        schema = vol.Schema({
            vol.Required("section", default="profile"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "profile", "label": "Sensores y comportamiento"},
                        {"value": "tariffs", "label": "Tarifas eléctricas"},
                        {"value": "units", "label": "Unidades y moneda"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_profile(self, user_input=None):
        """Edit sensor mappings and session finalization settings."""
        current = {**self.config_entry.data, **self.config_entry.options}
        errors = {}
        if user_input is not None:
            if user_input[CONF_FINALIZATION] == FINALIZE_ODOMETER and not user_input.get(CONF_ODOMETER_ENTITY):
                errors["base"] = "odometer_required"
            elif user_input[CONF_PRICE_MODE] == PRICE_MODE_SENSOR and not user_input.get(CONF_PRICE_ENTITY):
                errors["base"] = "price_sensor_required"
            else:
                # Options override the original config data. The storage key is
                # tied to entry_id, so changing mappings never discards history.
                return self.async_create_entry(
                    title="", data={**self.config_entry.options, **user_input}
                )

        schema = vol.Schema({
            vol.Required(CONF_CHARGING_ENTITY, default=current[CONF_CHARGING_ENTITY]): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Required(CONF_ENERGY_ENTITY, default=current[CONF_ENERGY_ENTITY]): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_POWER_ENTITY, default=current.get(CONF_POWER_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_ENERGY_MODE, default=current.get(CONF_ENERGY_MODE, ENERGY_MODE_SESSION)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": ENERGY_MODE_SESSION, "label": "Energía de sesión (se reinicia en cada carga)"},
                        {"value": ENERGY_MODE_CUMULATIVE, "label": "Contador acumulativo"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(CONF_SOC_ENTITY, default=current.get(CONF_SOC_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_ODOMETER_ENTITY, default=current.get(CONF_ODOMETER_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_ODOMETER_UNIT, default=current.get(CONF_ODOMETER_UNIT, "km")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "km", "label": "Kilómetros"},
                        {"value": "mi", "label": "Millas"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_PRICE_MODE, default=current.get(CONF_PRICE_MODE, PRICE_MODE_MANUAL)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": PRICE_MODE_MANUAL, "label": "Precio manual fijo"},
                        {"value": PRICE_MODE_SENSOR, "label": "Precio desde sensor"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(CONF_PRICE, default=current.get(CONF_PRICE, 0.11)): All(Coerce(float), Range(min=0)),
            vol.Optional(CONF_PRICE_ENTITY, default=current.get(CONF_PRICE_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_FINALIZATION, default=current.get(CONF_FINALIZATION, FINALIZE_ODOMETER)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": FINALIZE_ODOMETER, "label": "Cuando aumente el odómetro"},
                        {"value": FINALIZE_IMMEDIATE, "label": "Al terminar la carga"},
                        {"value": FINALIZE_MANUAL, "label": "Confirmación manual"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })
        return self.async_show_form(step_id="profile", data_schema=schema, errors=errors)


    async def async_step_units(self, user_input=None):
        """Configure display units and currency independently of source units."""
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            currency = user_input[CONF_CURRENCY].strip().upper()
            if len(currency) != 3 or not currency.isalpha() or not currency.isascii():
                return self.async_show_form(
                    step_id="units", data_schema=self._units_schema(current),
                    errors={"base": "invalid_currency"},
                )
            user_input[CONF_CURRENCY] = currency
            return self.async_create_entry(
                title="", data={**self.config_entry.options, **user_input}
            )
        return self.async_show_form(step_id="units", data_schema=self._units_schema(current))

    def _units_schema(self, current):
        """Build the international unit preference selector."""
        def choices(values):
            return selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": value, "label": label} for value, label in values],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        return vol.Schema({
            vol.Required(CONF_UNIT_ENERGY, default=current.get(CONF_UNIT_ENERGY, "kWh")): choices([
                ("Wh", "Wh"), ("kWh", "kWh"), ("MWh", "MWh")]),
            vol.Required(CONF_UNIT_DISTANCE, default=current.get(CONF_UNIT_DISTANCE, "km")): choices([
                ("m", "m"), ("km", "km"), ("mi", "mi"), ("ft", "ft")]),
            vol.Required(CONF_UNIT_POWER, default=current.get(CONF_UNIT_POWER, "kW")): choices([
                ("W", "W"), ("kW", "kW"), ("MW", "MW")]),
            vol.Required(CONF_UNIT_VOLTAGE, default=current.get(CONF_UNIT_VOLTAGE, "V")): choices([
                ("mV", "mV"), ("V", "V"), ("kV", "kV")]),
            vol.Required(CONF_UNIT_CURRENT, default=current.get(CONF_UNIT_CURRENT, "A")): choices([
                ("mA", "mA"), ("A", "A"), ("kA", "kA")]),
            vol.Required(CONF_UNIT_TEMPERATURE, default=current.get(CONF_UNIT_TEMPERATURE, "°C")): choices([
                ("°C", "°C"), ("°F", "°F"), ("K", "K")]),
            vol.Required(CONF_UNIT_CONSUMPTION, default=current.get(CONF_UNIT_CONSUMPTION, "kWh/100km")): choices([
                ("kWh/100km", "kWh/100 km"), ("Wh/km", "Wh/km"),
                ("km/kWh", "km/kWh"), ("mi/kWh", "mi/kWh"), ("kWh/100mi", "kWh/100 mi")]),
            vol.Required(CONF_CURRENCY, default=current.get(CONF_CURRENCY, "EUR")): str,
        })

    async def async_step_tariffs(self, user_input=None):
        """Choose the number of tariff periods."""
        saved = self.config_entry.options.get(
            CONF_TARIFF_PERIODS, self.config_entry.data.get(CONF_TARIFF_PERIODS)
        ) or []
        current_count = len(saved) if saved else 1
        if user_input is not None:
            self._period_count = int(user_input[CONF_TARIFF_COUNT])
            defaults = default_periods(self._period_count)
            self._period_drafts = [
                {**defaults[index], **saved[index]}
                if index < len(saved) else defaults[index]
                for index in range(self._period_count)
            ]
            self._period_index = 0
            return await self.async_step_periods()
        schema = vol.Schema({
            vol.Required(CONF_TARIFF_COUNT, default=str(current_count)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "1", "label": "Un periodo (precio único)"},
                        {"value": "2", "label": "Dos periodos"},
                        {"value": "3", "label": "Tres periodos"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        })
        return self.async_show_form(step_id="tariffs", data_schema=schema)

    async def async_step_periods(self, user_input=None):
        """Collect schedule details and choose a price source for every period."""
        errors = {}
        if user_input is not None:
            drafts = []
            for index in range(1, self._period_count + 1):
                previous = self._period_drafts[index - 1]
                source = user_input[f"period_{index}_price_source"]
                period = {
                    "name": user_input[f"period_{index}_name"].strip(),
                    "start": user_input[f"period_{index}_start"],
                    "end": user_input[f"period_{index}_end"],
                    "days": [int(day) for day in user_input[f"period_{index}_days"]],
                    "_price_source": source,
                }
                # Retain the inactive source's previous value so switching
                # back later does not destroy the user's previous setting.
                if previous.get("price") is not None:
                    period["price"] = previous["price"]
                if previous.get("price_entity"):
                    period["price_entity"] = previous["price_entity"]
                if previous.get("price_entity_backup"):
                    period["price_entity_backup"] = previous["price_entity_backup"]
                drafts.append(period)
            self._period_drafts = drafts
            self._period_index = 0
            return await self.async_step_period_price()

        return self.async_show_form(
            step_id="periods",
            data_schema=self._period_details_schema(self._period_drafts),
            errors=errors,
        )

    async def async_step_period_price(self, user_input=None):
        """Ask only for the selected source: manual price or price sensor."""
        index = self._period_index
        period = self._period_drafts[index]
        source = period.get("_price_source", "sensor" if period.get("price_entity") else "manual")

        if user_input is not None:
            if source == "manual":
                period["price"] = float(user_input["price"])
                # Keep the previous sensor selection separately so switching
                # back to sensor pricing does not discard the user's choice.
                if period.get("price_entity"):
                    period["price_entity_backup"] = period["price_entity"]
                period.pop("price_entity", None)
            else:
                period["price_entity"] = user_input["price_entity"]
                period["price_entity_backup"] = user_input["price_entity"]
                # Keep a prior manual value hidden for a future source switch,
                # but tariff validation and calculation treat the active sensor as exclusive.
            self._period_drafts[index] = period
            if index + 1 < self._period_count:
                self._period_index += 1
                return await self.async_step_period_price()

            periods = []
            for draft in self._period_drafts:
                saved_period = {key: value for key, value in draft.items() if not key.startswith("_")}
                periods.append(saved_period)
            errors = validate_periods(periods)
            if errors:
                return self.async_show_form(
                    step_id="periods",
                    data_schema=self._period_details_schema(self._period_drafts),
                    errors={"base": "invalid_schedule"},
                    description_placeholders={"schedule_error": " ".join(errors)},
                )
            return self.async_create_entry(
                title="", data={**self.config_entry.options, CONF_TARIFF_PERIODS: periods}
            )

        return self.async_show_form(
            step_id="period_price",
            data_schema=self._period_price_schema(period, source),
            description_placeholders={
                "period_name": period.get("name", f"Periodo {index + 1}"),
                "period_number": str(index + 1),
            },
        )

    def _period_details_schema(self, existing):
        """Build the shared schedule/source form, without showing inactive price fields."""
        day_options = [
            {"value": "0", "label": "Lunes"},
            {"value": "1", "label": "Martes"},
            {"value": "2", "label": "Miércoles"},
            {"value": "3", "label": "Jueves"},
            {"value": "4", "label": "Viernes"},
            {"value": "5", "label": "Sábado"},
            {"value": "6", "label": "Domingo"},
        ]
        schema = {}
        for index in range(1, self._period_count + 1):
            period = existing[index - 1]
            source = period.get(
                "_price_source", "sensor" if period.get("price_entity") else "manual"
            )
            schema[vol.Required(f"period_{index}_name", default=period["name"])] = str
            schema[vol.Required(f"period_{index}_start", default=period["start"])] = str
            schema[vol.Required(f"period_{index}_end", default=period["end"])] = str
            schema[vol.Required(
                f"period_{index}_price_source", default=source
            )] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "manual", "label": "Manual"},
                        {"value": "sensor", "label": "Sensor"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
            schema[vol.Required(
                f"period_{index}_days",
                default=[str(day) for day in period.get("days", list(range(7)))],
            )] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=day_options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        return vol.Schema(schema)

    @staticmethod
    def _period_price_schema(period, source):
        """Return a form containing exactly one active price source field."""
        if source == "manual":
            key = (
                vol.Required("price", default=period["price"])
                if period.get("price") is not None
                else vol.Required("price")
            )
            return vol.Schema({key: All(Coerce(float), Range(min=0))})
        key = (
            vol.Required(
                "price_entity",
                default=period.get("price_entity") or period.get("price_entity_backup"),
            )
            if period.get("price_entity") or period.get("price_entity_backup")
            else vol.Required("price_entity")
        )
        return vol.Schema({
            key: selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
        })
