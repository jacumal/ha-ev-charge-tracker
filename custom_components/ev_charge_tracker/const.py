"""Constants for EV Charge Tracker."""

from datetime import timedelta

DOMAIN = "ev_charge_tracker"
PLATFORMS = ["sensor"]

CONF_VEHICLE_NAME = "vehicle_name"
CONF_CHARGER_NAME = "charger_name"
CONF_CHARGING_ENTITY = "charging_entity"
CONF_ENERGY_ENTITY = "energy_entity"
CONF_ENERGY_MODE = "energy_mode"
CONF_SOC_ENTITY = "soc_entity"
CONF_ODOMETER_ENTITY = "odometer_entity"
CONF_ODOMETER_UNIT = "odometer_unit"
CONF_PRICE = "price_per_kwh"
CONF_FINALIZATION = "finalization"

ENERGY_MODE_SESSION = "session"
FINALIZE_ODOMETER = "odometer"
FINALIZE_IMMEDIATE = "immediate"
FINALIZE_MANUAL = "manual"

STORAGE_VERSION = 1
UPDATE_INTERVAL = timedelta(seconds=15)

DEFAULT_PRICE = 0.0
MAX_HISTORY = 500
