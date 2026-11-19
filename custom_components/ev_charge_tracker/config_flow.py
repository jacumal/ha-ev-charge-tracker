"""Config flow for EV Charge Tracker."""

from __future__ import annotations

import voluptuous as vol
from voluptuous import All, Coerce, Range

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .tariff import default_periods, validate_periods

from .const import (
    CONF_CHARGER_NAME,
    CONF_CHARGING_ENTITY,
    CONF_ENERGY_ENTITY,
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
    FINALIZE_IMMEDIATE,
    FINALIZE_ODOMETER,
    FINALIZE_MANUAL,
    PRICE_MODE_MANUAL,
    PRICE_MODE_SENSOR,
    CONF_TARIFF_PERIODS,
    CONF_TARIFF_COUNT,
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
                await self.async_set_unique_id(
                    f"{vehicle_name.lower()}_{charger_name.lower()}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{vehicle_name} · {charger_name}",
                    data=user_input,
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
                vol.Required(CONF_ENERGY_MODE, default=ENERGY_MODE_SESSION): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": ENERGY_MODE_SESSION, "label": "Energía de la sesión (se reinicia en cada carga)"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
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
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_PRICE_MODE, default=PRICE_MODE_MANUAL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": PRICE_MODE_MANUAL, "label": "Precio manual fijo"},
                            {"value": PRICE_MODE_SENSOR, "label": "Precio desde sensor de Home Assistant"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
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
                        mode=selector.SelectSelectorMode.DROPDOWN,
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
    """Edit tariff periods without removing the profile or its history."""

    def __init__(self):
        self._period_count = 1

    async def async_step_init(self, user_input=None):
        """Choose the number of tariff periods."""
        existing = self.config_entry.options.get(
            CONF_TARIFF_PERIODS, self.config_entry.data.get(CONF_TARIFF_PERIODS)
        )
        current_count = len(existing) if existing else 1
        if user_input is not None:
            self._period_count = int(user_input[CONF_TARIFF_COUNT])
            return await self.async_step_periods()
        schema = vol.Schema({
            vol.Required(CONF_TARIFF_COUNT, default=current_count): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": 1, "label": "Un periodo (precio único)"},
                        {"value": 2, "label": "Dos periodos"},
                        {"value": 3, "label": "Tres periodos"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_periods(self, user_input=None):
        """Configure names, times, weekdays and prices."""
        saved = self.config_entry.options.get(
            CONF_TARIFF_PERIODS, self.config_entry.data.get(CONF_TARIFF_PERIODS)
        ) or []
        defaults = default_periods(self._period_count)
        existing = (saved + defaults)[0:self._period_count]
        if user_input is not None:
            periods = []
            for index in range(1, self._period_count + 1):
                periods.append({
                    "name": user_input[f"period_{index}_name"].strip(),
                    "start": user_input[f"period_{index}_start"],
                    "end": user_input[f"period_{index}_end"],
                    "price": float(user_input[f"period_{index}_price"]),
                    "days": user_input[f"period_{index}_days"],
                })
            errors = validate_periods(periods)
            if not errors:
                return self.async_create_entry(
                    title="", data={CONF_TARIFF_PERIODS: periods}
                )
            existing = periods
            return self.async_show_form(
                step_id="periods",
                data_schema=self._period_schema(existing),
                errors={"base": "invalid_schedule"},
                description_placeholders={"schedule_error": " ".join(errors)},
            )
        return self.async_show_form(
            step_id="periods", data_schema=self._period_schema(existing)
        )

    def _period_schema(self, existing):
        day_options = [
            {"value": 0, "label": "Lunes"},
            {"value": 1, "label": "Martes"},
            {"value": 2, "label": "Miércoles"},
            {"value": 3, "label": "Jueves"},
            {"value": 4, "label": "Viernes"},
            {"value": 5, "label": "Sábado"},
            {"value": 6, "label": "Domingo"},
        ]
        schema = {}
        for index in range(1, self._period_count + 1):
            period = existing[index - 1]
            schema[vol.Required(f"period_{index}_name", default=period["name"])] = str
            schema[vol.Required(f"period_{index}_start", default=period["start"])] = str
            schema[vol.Required(f"period_{index}_end", default=period["end"])] = str
            schema[vol.Required(f"period_{index}_price", default=period["price"])] = All(
                Coerce(float), Range(min=0)
            )
            schema[vol.Required(
                f"period_{index}_days",
                default=period.get("days", list(range(7))),
            )] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=day_options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        return vol.Schema(schema)
