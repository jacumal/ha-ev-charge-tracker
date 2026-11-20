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
