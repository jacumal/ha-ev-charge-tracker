"""EV Charge Tracker integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import EVChargeCoordinator
from .profile_registry import build_profile_registry

EVChargeConfigEntry = ConfigEntry[EVChargeCoordinator]
REGISTRY_DATA_KEY = "_profile_registry"
CARD_URL = "/ev_charge_tracker/ev-charge-tracker-card.js"


def _refresh_profile_registry(hass: HomeAssistant) -> None:
    """Refresh read-only vehicle, charger and profile indexes."""
    entries = hass.config_entries.async_entries(DOMAIN)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][REGISTRY_DATA_KEY] = build_profile_registry(entries)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration and serve its bundled Lovelace card."""
    hass.data.setdefault(DOMAIN, {})
    _refresh_profile_registry(hass)
    card_path = Path(__file__).parent / "frontend" / "ev-charge-tracker-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), cache_headers=True)]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EVChargeConfigEntry) -> bool:
    """Set up a configured vehicle/charger profile."""
    coordinator = EVChargeCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})
    try:
        await coordinator.async_setup()
        await coordinator.async_config_entry_first_refresh()

        hass.data[DOMAIN][entry.entry_id] = coordinator
        _refresh_profile_registry(hass)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        return True
    except Exception:
        # async_setup() subscribes to source entities before the first refresh
        # and platform forwarding can still fail afterwards. Always release
        # those listeners and persist the restored session on failed setup.
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await coordinator.async_shutdown()
        _refresh_profile_registry(hass)
        raise


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
