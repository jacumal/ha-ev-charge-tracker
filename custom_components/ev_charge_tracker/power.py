"""Power-based allocation helpers for EV charging energy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any

from .tariff import active_period, allocate_energy_by_time


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Power samples and interval timestamps must be timezone-aware.")
    return value.astimezone(timezone.utc)


def allocate_energy_by_power(
    start: datetime,
    end: datetime,
    energy_kwh: float,
    periods: list[dict[str, Any]],
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Allocate meter-confirmed energy using trapezoidal power integration.

    The energy meter remains authoritative: integrated power determines the
    relative distribution over time, then allocations are scaled to its exact
    delta. Power is linearly interpolated between samples and held at the
    nearest sample at interval edges. Tariff changes are split at minute
    boundaries and at every power sample.
    """
    start_utc, end_utc = _utc(start), _utc(end)
    if end_utc <= start_utc or not math.isfinite(energy_kwh) or energy_kwh < 0:
        raise ValueError("Invalid energy or time interval.")

    points: list[tuple[datetime, float]] = []
    for sample in samples:
        try:
            stamp = datetime.fromisoformat(str(sample["at"]))
            power = float(sample["power_kw"])
            stamp = _utc(stamp)
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(power) and power >= 0:
            points.append((stamp, power))
    points.sort(key=lambda item: item[0])
    # Keep the latest value for duplicate timestamps.
    deduped: dict[datetime, float] = {stamp: power for stamp, power in points}
    points = sorted(deduped.items())
    if not points or (start_utc - points[0][0]).total_seconds() > 300 or (end_utc - points[-1][0]).total_seconds() > 300:
        result = allocate_energy_by_time(start, end, energy_kwh, periods)
        result["method"] = "time_fallback"
        return result

    def power_at(moment: datetime) -> float:
        if moment <= points[0][0]:
            return points[0][1]
        if moment >= points[-1][0]:
            return points[-1][1]
        for (left_t, left_p), (right_t, right_p) in zip(points, points[1:]):
            if left_t <= moment <= right_t:
                span = (right_t - left_t).total_seconds()
                ratio = (moment - left_t).total_seconds() / span
                return left_p + (right_p - left_p) * ratio
        return points[-1][1]

    boundaries = {start_utc, end_utc}
    for stamp, _ in points:
        if start_utc < stamp < end_utc:
            boundaries.add(stamp)
    cursor = start_utc
    while cursor < end_utc:
        next_minute = cursor.replace(second=0, microsecond=0) + timedelta(minutes=1)
        cursor = min(next_minute, end_utc)
        boundaries.add(cursor)

    ordered = sorted(boundaries)
    segments: list[tuple[str, float]] = []
    for left, right in zip(ordered, ordered[1:]):
        local = left.astimezone(start.tzinfo)
        period = active_period(local, periods)
        if period is None:
            raise ValueError(f"No tariff configured for {local.isoformat()}")
        p0, p1 = power_at(left), power_at(right)
        raw_energy = ((p0 + p1) / 2.0) * ((right - left).total_seconds() / 3600.0)
        segments.append((str(period.get("name", "Period")), raw_energy))

    raw_total = sum(max(0.0, value) for _, value in segments)
    if raw_total <= 0:
        result = allocate_energy_by_time(start, end, energy_kwh, periods)
        result["method"] = "time_fallback"
        return result

    totals: dict[str, float] = {}
    allocated = 0.0
    for index, (name, raw) in enumerate(segments):
        amount = energy_kwh - allocated if index == len(segments) - 1 else energy_kwh * max(0.0, raw) / raw_total
        allocated += amount
        totals[name] = totals.get(name, 0.0) + amount

    breakdown = []
    total_cost = 0.0
    for name, amount in totals.items():
        period = next(item for item in periods if str(item.get("name", "Period")) == name)
        price = float(period["price"])
        cost = amount * price
        total_cost += cost
        breakdown.append({
            "period": name,
            "energy_kwh": round(amount, 6),
            "price_per_kwh": price,
            "cost": round(cost, 6),
        })
    return {
        "energy_kwh": round(energy_kwh, 6),
        "cost": round(total_cost, 6),
        "estimated": True,
        "method": "power",
        "breakdown": breakdown,
    }
