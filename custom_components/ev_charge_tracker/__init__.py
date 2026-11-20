"""EV Charge Tracker integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import EVChargeCoordinator
from .profile_registry import build_profile_registry

EVChargeConfigEntry = ConfigEntry[EVChargeCoordinator]
REGISTRY_DATA_KEY = "_profile_registry"


def _refresh_profile_registry(hass: HomeAssistant) -> None:
    """Refresh read-only vehicle, charger and profile indexes."""
    entries = hass.config_entries.async_entries(DOMAIN)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][REGISTRY_DATA_KEY] = build_profile_registry(entries)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    _refresh_profile_registry(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EVChargeConfigEntry) -> bool:
    """Set up a configured vehicle/charger profile."""
    coordinator = EVChargeCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _refresh_profile_registry(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EVChargeConfigEntry) -> bool:
    """Unload a configured profile."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        _refresh_profile_registry(hass)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: EVChargeConfigEntry) -> None:
    """Reload the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
