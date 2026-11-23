"""Stable identity helpers for vehicle and charger profiles.

Names are presentation values; generated IDs are normalized identifiers and
must not be used as display names or as a substitute for Home Assistant entry IDs.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping


def normalize_profile_id(value: str) -> str:
    """Return a deterministic ASCII identifier from a user-facing name."""
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    if not slug:
        raise ValueError("Profile name must contain at least one letter or number")
    return slug


def build_profile_identity(vehicle_name: str, charger_name: str) -> dict[str, str]:
    """Build stable normalized identifiers while preserving display names elsewhere."""
    return {
        "vehicle_id": normalize_profile_id(vehicle_name),
        "charger_id": normalize_profile_id(charger_name),
    }


def find_resource_conflicts(
    candidate: Mapping[str, str],
    existing_profiles: Iterable[Mapping[str, str]],
) -> set[str]:
    """Return sensor roles already assigned to another configured profile.

    Charging state and delivered-energy meters are ownership-defining resources.
    Other telemetry (SOC, odometer, power) may legitimately be shared.
    """
    conflicts: set[str] = set()
    for profile in existing_profiles:
        for role in ("charging_entity", "energy_entity"):
            entity_id = candidate.get(role)
            if entity_id and entity_id == profile.get(role):
                conflicts.add(role)
    return conflicts



def _legacy_identity(name: str | None, entry_id: str, resource: str) -> str:
    """Return a read-only fallback identity for entries created before registry IDs."""
    if name and name.strip():
        try:
            return normalize_profile_id(name)
        except ValueError:
            pass
    return f"legacy_{resource}_{normalize_profile_id(entry_id)}"


def build_profile_registry(config_entries: Iterable[object]) -> dict[str, dict]:
    """Build in-memory vehicle, charger and profile indexes from config entries.

    The function is deliberately read-only: it never writes migrations or
    changes config-entry data. Legacy entries receive deterministic fallback
    identities, while their entry_id remains the storage/lifecycle namespace.
    """
    vehicles: dict[str, dict] = {}
    chargers: dict[str, dict] = {}
    profiles: dict[str, dict] = {}

    for entry in config_entries:
        entry_id = str(getattr(entry, "entry_id", "") or "")
        data = dict(getattr(entry, "data", {}) or {})
        options = dict(getattr(entry, "options", {}) or {})
        config = {**data, **options}
        vehicle_name = str(config.get("vehicle_name") or "").strip()
        charger_name = str(config.get("charger_name") or "").strip()
        vehicle_id = config.get("vehicle_id") or _legacy_identity(
            vehicle_name, entry_id, "vehicle"
        )
        charger_id = config.get("charger_id") or _legacy_identity(
            charger_name, entry_id, "charger"
        )
        legacy = not (config.get("vehicle_id") and config.get("charger_id"))

        profile = {
            "entry_id": entry_id,
            "vehicle_id": vehicle_id,
            "charger_id": charger_id,
            "vehicle_name": vehicle_name or vehicle_id,
            "charger_name": charger_name or charger_id,
            "legacy": legacy,
            "charging_entity": config.get("charging_entity"),
            "energy_entity": config.get("energy_entity"),
            "soc_entity": config.get("soc_entity"),
            "odometer_entity": config.get("odometer_entity"),
            "power_entity": config.get("power_entity"),
            "plugged_entity": config.get("plugged_entity"),
            "vehicle_visual": {
                key: config.get(key)
                for key in (
                    "visual_brand", "visual_model", "visual_generation", "visual_year",
                    "visual_trim", "visual_color", "visual_body_style", "visual_image",
                )
                if config.get(key) not in (None, "")
            },
        }
        profiles[entry_id] = profile

        vehicle = vehicles.setdefault(vehicle_id, {
            "vehicle_id": vehicle_id,
            "name": profile["vehicle_name"],
            "profile_ids": [],
            "visual": {},
        })
        if entry_id not in vehicle["profile_ids"]:
            vehicle["profile_ids"].append(entry_id)
        # Visual identity belongs to the vehicle, not an individual charger.
        # Keep previously saved non-empty values when another charger profile
        # for the same vehicle has no visual settings of its own.
        vehicle["visual"].update(profile["vehicle_visual"])
        profile["vehicle_visual"] = vehicle["visual"]

        charger = chargers.setdefault(charger_id, {
            "charger_id": charger_id,
            "name": profile["charger_name"],
            "profile_ids": [],
            "charging_entities": set(),
            "energy_entities": set(),
        })
        if entry_id not in charger["profile_ids"]:
            charger["profile_ids"].append(entry_id)
        if profile["charging_entity"]:
            charger["charging_entities"].add(profile["charging_entity"])
        if profile["energy_entity"]:
            charger["energy_entities"].add(profile["energy_entity"])

    conflicts: dict[str, list[str]] = {}
    for role in ("charging_entity", "energy_entity"):
        owners: dict[str, list[str]] = {}
        for entry_id, profile in profiles.items():
            entity_id = profile[role]
            if entity_id:
                owners.setdefault(entity_id, []).append(entry_id)
        for entity_id, entry_ids in owners.items():
            if len(entry_ids) > 1:
                conflicts[f"{role}:{entity_id}"] = entry_ids

    return {
        "vehicles": vehicles,
        "chargers": chargers,
        "profiles": profiles,
        "conflicts": conflicts,
    }
