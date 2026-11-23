"""Authenticated WebSocket API for the Lovelace card."""

from __future__ import annotations

from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

from .const import DOMAIN

PROFILE_COMMAND = "ev_charge_tracker/profiles"
SENSOR_KEYS = (
    "status",
    "energy",
    "cost",
    "soc_start",
    "soc_end",
    "soc_increase",
    "duration",
    "history",
)


@websocket_api.websocket_command({vol.Required("type"): PROFILE_COMMAND})
@websocket_api.async_response
async def websocket_get_profiles(hass, connection, msg):
    """Return configured profiles and their generated tracker sensor entities."""
    registry = er.async_get(hass)
    data = hass.data.get(DOMAIN, {}).get("_profile_registry", {})
    profiles = []
    for entry_id, profile in data.get("profiles", {}).items():
        entities = {
            key: registry.async_get_entity_id("sensor", DOMAIN, f"{entry_id}_{key}")
            for key in SENSOR_KEYS
        }
        # Expose the source telemetry selected in the profile as read-only card
        # entities. These are existing HA entities, not new tracker sensors.
        entities["current_soc"] = profile.get("soc_entity")
        entities["odometer"] = profile.get("odometer_entity")
        profiles.append(
            {
                "entry_id": entry_id,
                "vehicle_name": profile.get("vehicle_name") or "Vehículo",
                "charger_name": profile.get("charger_name") or "Cargador",
                "entities": entities,
            }
        )
    connection.send_result(msg["id"], {"profiles": profiles})


def async_register(hass) -> None:
    """Register the card's profile discovery command."""
    websocket_api.async_register_command(hass, websocket_get_profiles)
