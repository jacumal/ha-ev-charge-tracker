"""Sensors exposed by EV Charge Tracker."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EVChargeConfigEntry
from .const import (
    CONF_VEHICLE_NAME, DOMAIN, CONF_UNIT_ENERGY, CONF_CURRENCY,
)
from .coordinator import EVChargeCoordinator
from .units import convert_unit


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

    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "energy", "Energía de la carga", "mdi:lightning-bolt")
        self._unit = coordinator.config.get(CONF_UNIT_ENERGY, "kWh")
        self._attr_native_unit_of_measurement = self._unit

    @property
    def native_value(self):
        session = self.coordinator.data.get("session")
        latest = self.coordinator.data.get("latest")
        record = session or latest
        if not record or record.get("energy_kwh") is None:
            return None
        return convert_unit(record["energy_kwh"], "energy", "kWh", self._unit)


class EVChargeCostSensor(EVChargeBaseSensor):
    """Cost of latest/current session."""

    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "cost", "Coste de la carga", "mdi:cash")
        self._attr_native_unit_of_measurement = coordinator.config.get(CONF_CURRENCY, "EUR")

    def _record(self):
        return self.coordinator.data.get("session") or self.coordinator.data.get("latest") or {}

    def _known_cost(self, record):
        buckets = record.get("tariff_breakdown") or {}
        if buckets:
            return round(sum(item.get("cost", 0.0) for item in buckets.values()), 4)
        energy = record.get("energy_kwh")
        price = record.get("price_per_kwh")
        if record.get("energy_valid") and energy is not None and price is not None:
            return round(energy * price, 4)
        return record.get("known_cost")

    @property
    def native_value(self):
        record = self._record()
        if not record:
            return None
        if record.get("status") == "completed":
            return record.get("cost")
        energy = record.get("energy_kwh")
        complete = bool(
            record.get("cost_complete", True)
            and record.get("energy_valid")
            and energy is not None
            and record.get("priced_energy_kwh", 0.0) >= energy - 0.0001
        )
        known_cost = self._known_cost(record)
        return round(known_cost, 2) if complete and known_cost is not None else None

    @property
    def extra_state_attributes(self):
        record = self._record()
        energy = record.get("energy_kwh")
        complete = bool(
            record.get("cost_complete", True)
            and record.get("energy_valid")
            and energy is not None
            and record.get("priced_energy_kwh", 0.0) >= energy - 0.0001
        )
        known_cost = self._known_cost(record)
        if record.get("status") == "completed":
            cost_status = record.get("cost_status", "unknown")
        elif known_cost is not None:
            cost_status = "in_progress" if complete else "partial"
        else:
            cost_status = "unknown"
        return {
            "cost_status": cost_status,
            "known_cost": known_cost,
            "currency": record.get("currency", self.coordinator.config.get(CONF_CURRENCY, "EUR")),
            "priced_energy_kwh": record.get("priced_energy_kwh", 0.0),
            "unpriced_energy_kwh": record.get("unpriced_energy_kwh", 0.0),
            "cost_complete": complete,
            "tariff_breakdown": record.get("tariff_breakdown", {}),
            "tariff_estimated": record.get("tariff_estimated", False),
            "tariff_allocation_method": record.get("tariff_allocation_method"),
        }


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
