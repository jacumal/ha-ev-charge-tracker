"""International unit registry and explicit conversions.

Internal canonical units: kWh, kW, km, V, A, °C and kWh/100 km.
Currency is deliberately not converted: exchange-rate conversion would require
a dated FX source and must never be guessed.
"""
from __future__ import annotations

import re

UNIT_ALIASES = {
    "energy": {
        "wh": ("wh", 0.001), "kwh": ("kwh", 1.0), "mwh": ("mwh", 1000.0),
        "j": ("j", 1 / 3_600_000), "mj": ("mj", 1 / 3.6),
    },
    "power": {"w": ("w", 0.001), "kw": ("kw", 1.0), "mw": ("mw", 1000.0)},
    "distance": {
        "m": ("m", 0.001), "km": ("km", 1.0),
        "mi": ("mi", 1.609344), "mile": ("mi", 1.609344),
        "ft": ("ft", 0.0003048), "yd": ("yd", 0.0009144),
    },
    "voltage": {"mv": ("mv", 0.001), "v": ("v", 1.0), "kv": ("kv", 1000.0)},
    "current": {"ma": ("ma", 0.001), "a": ("a", 1.0), "ka": ("ka", 1000.0)},
    "temperature": {"°c": ("c", 1.0), "c": ("c", 1.0), "°f": ("f", 1.0), "f": ("f", 1.0), "k": ("k", 1.0)},
    "consumption": {
        "kwh/100km": ("kwh_100km", 1.0),
        "wh/km": ("wh_km", 0.1),
        "km/kwh": ("km_kwh", 1.0),
        "mi/kwh": ("mi_kwh", 1.609344),
        "kwh/100mi": ("kwh_100mi", 0.621371192237334),
    },
}

CANONICAL_UNITS = {
    "energy": "kWh", "power": "kW", "distance": "km",
    "voltage": "V", "current": "A", "temperature": "°C",
    "consumption": "kWh/100km",
}

def _key(unit: str) -> str:
    return re.sub(r"\\s+", "", (unit or "").strip().lower())

def convert_unit(value: float, dimension: str, from_unit: str, to_unit: str) -> float:
    """Convert a numeric value between supported units of one dimension."""
    if dimension not in UNIT_ALIASES:
        raise ValueError(f"Unsupported dimension: {dimension}")
    aliases = UNIT_ALIASES[dimension]
    source = aliases.get(_key(from_unit))
    target = aliases.get(_key(to_unit))
    if source is None or target is None:
        raise ValueError(f"Unsupported {dimension} unit: {from_unit} or {to_unit}")
    number = float(value)
    if dimension == "temperature":
        source_key, target_key = source[0], target[0]
        if source_key == "f":
            number = (number - 32) * 5 / 9
        elif source_key == "k":
            number -= 273.15
        if target_key == "f":
            number = number * 9 / 5 + 32
        elif target_key == "k":
            number += 273.15
        return number
    if dimension == "consumption":
        # Convert all rates to kWh/100km before converting to target.
        source_key, target_key = source[0], target[0]
        if source_key == "kwh_100km":
            canonical = number
        elif source_key == "wh_km":
            canonical = number / 10
        elif source_key == "km_kwh":
            canonical = 100 / number if number else 0.0
        elif source_key == "mi_kwh":
            canonical = 100 / (number * 1.609344) if number else 0.0
        else:  # kWh/100mi
            canonical = number / 1.609344
        if target_key == "kwh_100km":
            return canonical
        if target_key == "wh_km":
            return canonical * 10
        if target_key == "km_kwh":
            return 100 / canonical if canonical else 0.0
        if target_key == "mi_kwh":
            return 100 / (canonical * 1.609344) if canonical else 0.0
        return canonical * 1.609344
    canonical = number * source[1]
    return canonical / target[1]

def normalize_currency_code(value: str) -> str:
    """Validate and normalize a user-selected ISO 4217-style currency code."""
    code = (value or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise ValueError("Currency must be a three-letter ISO code, e.g. EUR or USD")
    return code
