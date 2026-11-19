"""Sensors exposed by EV Charge Tracker."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EVChargeConfigEntry
from .const import CONF_VEHICLE_NAME, DOMAIN
from .coordinator import EVChargeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EVChargeConfigEntry,
    async_add_entities,
) -> None:
    """Set up profile sensors."""
    coordinator: EVChargeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            EVChargeStatusSensor(coordinator, entry),
            EVChargeEnergySensor(coordinator, entry),
            EVChargeCostSensor(coordinator, entry),
            EVChargeSocStartSensor(coordinator, entry),
            EVChargeSocEndSensor(coordinator, entry),
            EVChargeSocIncreaseSensor(coordinator, entry),
            EVChargeDurationSensor(coordinator, entry),
            EVChargeHistorySensor(coordinator, entry),
        ]
    )


class EVChargeBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for profile sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key, name, icon):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_VEHICLE_NAME],
            manufacturer="EV Charge Tracker",
            model="Charging profile",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class EVChargeStatusSensor(EVChargeBaseSensor):
    """Current session status."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "status", "Estado de carga", "mdi:ev-station")


class EVChargeEnergySensor(EVChargeBaseSensor):
    """Energy delivered by the latest/current session."""

    _attr_native_unit_of_measurement = "kWh"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "energy", "Energía de la carga", "mdi:lightning-bolt")

    @property
    def native_value(self):
        session = self.coordinator.data.get("session")
        latest = self.coordinator.data.get("latest")
        record = session or latest
        return record.get("energy_kwh") if record else None


class EVChargeCostSensor(EVChargeBaseSensor):
    """Cost of latest/current session."""

    _attr_native_unit_of_measurement = "€"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "cost", "Coste de la carga", "mdi:currency-eur")

    @property
    def native_value(self):
        session = self.coordinator.data.get("session")
        latest = self.coordinator.data.get("latest")
        record = session or latest
        return record.get("cost") if record else None


class EVChargeSocStartSensor(EVChargeBaseSensor):
    """SOC at session start."""

    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "soc_start", "Batería al inicio", "mdi:battery-arrow-up-outline")

    @property
    def native_value(self):
        record = self.coordinator.data.get("session") or self.coordinator.data.get("latest")
        return record.get("soc_start") if record else None


class EVChargeSocEndSensor(EVChargeBaseSensor):
    """SOC at session end."""

    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "soc_end", "Batería al final", "mdi:battery-check")

    @property
    def native_value(self):
        record = self.coordinator.data.get("session") or self.coordinator.data.get("latest")
        return record.get("soc_end") if record else None



class EVChargeSocIncreaseSensor(EVChargeBaseSensor):
    """SOC percentage-point increase during the charge."""

    _attr_native_unit_of_measurement = "pp"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "soc_increase", "Aumento de batería", "mdi:battery-plus")

    @property
    def native_value(self):
        record = self.coordinator.data.get("session") or self.coordinator.data.get("latest")
        if not record or record.get("soc_start") is None or record.get("soc_end") is None:
            return None
        return round(record["soc_end"] - record["soc_start"], 1)


class EVChargeDurationSensor(EVChargeBaseSensor):
    """Duration of latest/current charge in minutes."""

    _attr_native_unit_of_measurement = "min"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "duration", "Duración de la carga", "mdi:timer-outline")

    @property
    def native_value(self):
        record = self.coordinator.data.get("session") or self.coordinator.data.get("latest")
        if not record or not record.get("started_at"):
            return None
        start = datetime.fromisoformat(record["started_at"])
        end_value = record.get("ended_at") or datetime.now(start.tzinfo)
        return round((datetime.fromisoformat(end_value) - start).total_seconds() / 60, 1)


class EVChargeHistorySensor(EVChargeBaseSensor):
    """Persistent history as attributes."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "history", "Histórico de cargas", "mdi:history")

    @property
    def native_value(self):
        return len(self.coordinator.data.get("history", []))

    @property
    def extra_state_attributes(self):
        current = self.coordinator.data.get("session")
        latest = self.coordinator.data.get("latest")
        return {
            "sessions": self.coordinator.data.get("history", []),
            "current_session": current,
            "latest_session": latest,
            "diagnostic": self.coordinator.data.get("diagnostic"),
            "tariff_breakdown": (current or latest or {}).get("tariff_breakdown", {}),
            "tariff_estimated": (current or latest or {}).get("tariff_estimated", False),
        }
