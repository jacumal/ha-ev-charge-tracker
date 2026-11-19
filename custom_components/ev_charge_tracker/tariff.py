"""Time-of-use tariff helpers.

All schedule times are interpreted in the configured Home Assistant local timezone.
The helpers are deliberately independent from Home Assistant so they can be unit-tested.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import math
from typing import Any


def _parse_time(value: str) -> time:
    """Parse an HH:MM schedule boundary."""
    if value == "24:00":
        return time(0, 0)
    return time.fromisoformat(value)


def active_period(
    moment: datetime,
    periods: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the matching tariff period for a local datetime.

    Periods may cross midnight. The end boundary is exclusive.
    """
    weekday = moment.weekday()
    current = moment.timetz().replace(tzinfo=None)

    for period in periods:
        days = period.get("days", list(range(7)))
        start = _parse_time(period["start"])
        end = _parse_time(period["end"])

        if start == end and weekday in days:
            return period
        if start < end and weekday in days and start <= current < end:
            return period
        if start > end:
            if current >= start and weekday in days:
                return period
            if current < end and (weekday - 1) % 7 in days:
                return period

    return None


def validate_periods(periods: list[dict[str, Any]]) -> list[str]:
    """Return configuration errors for an incomplete/overlapping weekly schedule."""
    errors: list[str] = []
    if not 1 <= len(periods) <= 3:
        return ["Debe haber entre uno y tres periodos."]

    names = [str(period.get("name", "")).strip() for period in periods]
    if any(not name for name in names):
        errors.append("Todos los periodos deben tener un nombre.")
    if len(set(names)) != len(names):
        errors.append("Cada periodo debe tener un nombre distinto.")

    for index, period in enumerate(periods, start=1):
        try:
            _parse_time(period["start"])
            _parse_time(period["end"])
        except (KeyError, ValueError, TypeError):
            errors.append(f"Periodo {index}: horario no válido.")
        try:
            price = float(period["price"])
            if not math.isfinite(price):
                errors.append(f"Periodo {index}: el precio debe ser un número finito.")
            elif price < 0:
                errors.append(f"Periodo {index}: el precio no puede ser negativo.")
        except (KeyError, TypeError, ValueError):
            errors.append(f"Periodo {index}: falta un precio numérico.")
        days = period.get("days", list(range(7)))
        if not days or any(day not in range(7) for day in days):
            errors.append(f"Periodo {index}: selecciona días válidos.")

    # Check each minute of the weekly calendar. This catches gaps and overlaps,
    # including overnight periods and weekday-specific schedules.
    if not errors:
        monday = datetime(2024, 1, 1)  # Monday
        for minute in range(7 * 24 * 60):
            point = monday + timedelta(minutes=minute)
            matches = [
                period for period in periods
                if active_period(point, [period]) is not None
            ]
            if not matches:
                errors.append("El horario tiene huecos sin tarifa asignada.")
                break
            if len(matches) > 1:
                errors.append("El horario contiene periodos solapados.")
                break
    return errors


def allocate_energy_by_time(
    start: datetime,
    end: datetime,
    energy_kwh: float,
    periods: list[dict[str, Any]],
) -> dict[str, Any]:
    """Allocate an energy delta proportionally across tariff periods.

    This is an estimate when only energy-counter samples are available.
    A future power-integration path can provide a more accurate allocation.
    """
    aware = start.tzinfo is not None and end.tzinfo is not None
    if aware:
        timeline_start = start.astimezone(timezone.utc)
        timeline_end = end.astimezone(timezone.utc)
    else:
        timeline_start, timeline_end = start, end
    if timeline_end <= timeline_start or energy_kwh < 0:
        raise ValueError("Intervalo o energía no válidos.")

    seconds_by_period: dict[str, float] = {}
    # Walk the real timeline in UTC so DST changes do not create or lose elapsed time.
    cursor = timeline_start
    finish = timeline_end
    while cursor < finish:
        next_minute = cursor.replace(second=0, microsecond=0) + timedelta(minutes=1)
        boundary = min(next_minute, finish)
        local_cursor = cursor.astimezone(start.tzinfo) if aware else cursor
        period = active_period(local_cursor, periods)
        if period is None:
            raise ValueError(f"No hay tarifa configurada para {local_cursor.isoformat()}")
        key = str(period.get("name", "Periodo"))
        seconds_by_period[key] = seconds_by_period.get(key, 0.0) + (
            boundary - cursor
        ).total_seconds()
        cursor = boundary

    total_seconds = (finish - timeline_start).total_seconds()
    breakdown = []
    total_cost = 0.0
    allocated = 0.0
    items = list(seconds_by_period.items())
    for index, (name, seconds) in enumerate(items):
        energy = (
            energy_kwh - allocated
            if index == len(items) - 1
            else energy_kwh * seconds / total_seconds
        )
        allocated += energy
        period = next(p for p in periods if str(p.get("name", "Periodo")) == name)
        price = float(period["price"])
        cost = energy * price
        total_cost += cost
        breakdown.append({
            "period": name,
            "energy_kwh": round(energy, 6),
            "price_per_kwh": price,
            "cost": round(cost, 6),
        })

    return {
        "energy_kwh": round(energy_kwh, 6),
        "cost": round(total_cost, 6),
        "estimated": True,
        "breakdown": breakdown,
    }


def default_periods(count: int, price: float = 0.11) -> list[dict[str, Any]]:
    """Return editable starter schedules for one, two or three periods."""
    if count not in (1, 2, 3):
        raise ValueError("El número de periodos debe ser 1, 2 o 3.")
    if not math.isfinite(price) or price < 0:
        raise ValueError("El precio debe ser un número finito no negativo.")
    if count == 1:
        return [{"name": "Único", "start": "00:00", "end": "00:00",
                 "price": price, "days": list(range(7))}]
    if count == 2:
        return [
            {"name": "Valle", "start": "00:00", "end": "08:00",
             "price": price, "days": list(range(7))},
            {"name": "Punta", "start": "08:00", "end": "00:00",
             "price": price, "days": list(range(7))},
        ]
    return [
        {"name": "Valle", "start": "00:00", "end": "08:00",
         "price": price, "days": list(range(7))},
        {"name": "Llano", "start": "08:00", "end": "18:00",
         "price": price, "days": list(range(7))},
        {"name": "Punta", "start": "18:00", "end": "00:00",
         "price": price, "days": list(range(7))},
    ]
