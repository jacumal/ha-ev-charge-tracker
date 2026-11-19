"""Manual session finalization button."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FINALIZATION, CONF_VEHICLE_NAME, DOMAIN, FINALIZE_MANUAL


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EVChargeFinalizeButton(coordinator, entry)])


class EVChargeFinalizeButton(CoordinatorEntity, ButtonEntity):
    """Allow the user to confirm a stopped session."""

    _attr_has_entity_name = True
    _attr_name = "Consolidar última carga"
    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_manual_finalize"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_VEHICLE_NAME],
            manufacturer="EV Charge Tracker",
            model="Charging profile",
        )

    @property
    def available(self):
        session = self.coordinator.data.get("session")
        return bool(
            self.coordinator.config.get(CONF_FINALIZATION) == FINALIZE_MANUAL
            and session
            and session.get("ended_at")
            and session.get("energy_valid")
        )

    async def async_press(self) -> None:
        await self.coordinator.async_manual_finalize()
