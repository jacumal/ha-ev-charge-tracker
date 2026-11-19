"""Constants for EV Charge Tracker."""

from datetime import timedelta

DOMAIN = "ev_charge_tracker"
PLATFORMS = ["sensor", "button"]

CONF_VEHICLE_NAME = "vehicle_name"
CONF_CHARGER_NAME = "charger_name"
CONF_CHARGING_ENTITY = "charging_entity"
CONF_ENERGY_ENTITY = "energy_entity"
CONF_ENERGY_MODE = "energy_mode"
CONF_SOC_ENTITY = "soc_entity"
CONF_ODOMETER_ENTITY = "odometer_entity"
CONF_ODOMETER_UNIT = "odometer_unit"
CONF_PRICE = "price_per_kwh"
CONF_PRICE_MODE = "price_mode"
CONF_PRICE_ENTITY = "price_entity"
CONF_FINALIZATION = "finalization"
CONF_TARIFF_PERIODS = "tariff_periods"
CONF_TARIFF_COUNT = "tariff_period_count"
CONF_TARIFF_ENABLED = "tariff_enabled"

ENERGY_MODE_SESSION = "session"
ENERGY_MODE_CUMULATIVE = "cumulative"
PRICE_MODE_MANUAL = "manual"
PRICE_MODE_SENSOR = "sensor"
FINALIZE_ODOMETER = "odometer"
FINALIZE_IMMEDIATE = "immediate"
FINALIZE_MANUAL = "manual"

STORAGE_VERSION = 1
UPDATE_INTERVAL = timedelta(seconds=15)

DEFAULT_PRICE = 0.0
MAX_HISTORY = 500

# User-selected display units. Internal calculations remain canonical.
CONF_UNIT_ENERGY = "unit_energy"
CONF_UNIT_DISTANCE = "unit_distance"
CONF_UNIT_POWER = "unit_power"
CONF_UNIT_VOLTAGE = "unit_voltage"
CONF_UNIT_CURRENT = "unit_current"
CONF_UNIT_TEMPERATURE = "unit_temperature"
CONF_UNIT_CONSUMPTION = "unit_consumption"
CONF_CURRENCY = "currency"
