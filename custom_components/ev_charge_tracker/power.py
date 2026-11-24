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
    # Require telemetry close to both interval edges. Use absolute distance so
    # a future-dated sample cannot incorrectly make an old edge look fresh.
    start_distance = min(
        (abs((stamp - start_utc).total_seconds()) for stamp, _ in points),
        default=float("inf"),
    )
    end_distance = min(
        (abs((stamp - end_utc).total_seconds()) for stamp, _ in points),
        default=float("inf"),
    )
    if not points or start_distance > 300 or end_distance > 300:
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



def allocate_energy_by_dynamic_price(
    start: datetime,
    end: datetime,
    energy_kwh: float,
    periods: list[dict[str, Any]],
    power_samples: list[dict[str, Any]],
    price_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Allocate meter-confirmed energy and apply the price valid in each interval.

    Dynamic price samples are timestamped per tariff-period name. A missing or
    invalid sample for a dynamic period leaves that segment unpriced; it never
    silently reuses a stale price. Manual period prices remain supported.
    """
    start_utc, end_utc = _utc(start), _utc(end)
    if end_utc <= start_utc or not math.isfinite(energy_kwh) or energy_kwh < 0:
        raise ValueError("Invalid energy or time interval.")

    parsed_power: list[tuple[datetime, float]] = []
    for sample in power_samples:
        try:
            stamp = _utc(datetime.fromisoformat(str(sample["at"])))
            power = float(sample["power_kw"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(power) and power >= 0:
            parsed_power.append((stamp, power))
    parsed_power.sort(key=lambda item: item[0])
    power_map = {stamp: value for stamp, value in parsed_power}
    power_points = sorted(power_map.items())

    parsed_prices: dict[str, list[tuple[datetime, float | None]]] = {}
    for sample in price_samples:
        try:
            stamp = _utc(datetime.fromisoformat(str(sample["at"])))
            period_name = str(sample["period"])
        except (KeyError, TypeError, ValueError):
            continue
        raw_price = sample.get("price")
        try:
            price = float(raw_price) if raw_price is not None else None
        except (TypeError, ValueError):
            price = None
        if price is not None and (not math.isfinite(price) or price < 0):
            price = None
        parsed_prices.setdefault(period_name, []).append((stamp, price))
    for values in parsed_prices.values():
        values.sort(key=lambda item: item[0])

    # Use power weighting only when readings bracket both interval edges
    # closely. Otherwise retain the meter delta and fall back to elapsed time.
    start_distance = min((abs((stamp - start_utc).total_seconds()) for stamp, _ in power_points), default=float("inf"))
    end_distance = min((abs((stamp - end_utc).total_seconds()) for stamp, _ in power_points), default=float("inf"))
    use_power = bool(power_points) and start_distance <= 300 and end_distance <= 300

    def power_at(moment: datetime) -> float:
        if moment <= power_points[0][0]:
            return power_points[0][1]
        if moment >= power_points[-1][0]:
            return power_points[-1][1]
        for (left_t, left_p), (right_t, right_p) in zip(power_points, power_points[1:]):
            if left_t <= moment <= right_t:
                span = (right_t - left_t).total_seconds()
                ratio = (moment - left_t).total_seconds() / span
                return left_p + (right_p - left_p) * ratio
        return power_points[-1][1]

    boundaries = {start_utc, end_utc}
    for stamp, _ in power_points:
        if start_utc < stamp < end_utc:
            boundaries.add(stamp)
    for values in parsed_prices.values():
        for stamp, _ in values:
            if start_utc < stamp < end_utc:
                boundaries.add(stamp)
    cursor = start_utc
    while cursor < end_utc:
        cursor = min(cursor.replace(second=0, microsecond=0) + timedelta(minutes=1), end_utc)
        boundaries.add(cursor)
    ordered = sorted(boundaries)

    segments = []
    raw_total = 0.0
    for left, right in zip(ordered, ordered[1:]):
        local = left.astimezone(start.tzinfo)
        period = active_period(local, periods)
        if period is None:
            raise ValueError(f"No tariff configured for {local.isoformat()}")
        duration = (right - left).total_seconds()
        if use_power:
            weight = max(0.0, (power_at(left) + power_at(right)) / 2.0) * duration / 3600.0
        else:
            weight = duration
        raw_total += weight
        segments.append((left, right, period, weight))

    if raw_total <= 0:
        use_power = False
        raw_total = sum((right - left).total_seconds() for left, right, _, _ in segments)
        segments = [(left, right, period, (right - left).total_seconds()) for left, right, period, _ in segments]

    buckets: dict[str, dict[str, Any]] = {}
    allocated = 0.0
    for index, (left, right, period, weight) in enumerate(segments):
        amount = energy_kwh - allocated if index == len(segments) - 1 else energy_kwh * weight / raw_total
        allocated += amount
        name = str(period.get("name", "Period"))
        bucket = buckets.setdefault(name, {
            "period": name, "energy_kwh": 0.0, "cost": 0.0,
            "priced_energy_kwh": 0.0, "unpriced_energy_kwh": 0.0,
            "price_segments": [],
        })
        bucket["energy_kwh"] += amount

        price = None
        if period.get("price_entity"):
            candidates = [value for stamp, value in parsed_prices.get(name, []) if stamp <= left]
            price = candidates[-1] if candidates else None
        else:
            try:
                price = float(period["price"])
            except (KeyError, TypeError, ValueError):
                price = None
            if price is not None and (not math.isfinite(price) or price < 0):
                price = None

        if price is None:
            bucket["unpriced_energy_kwh"] += amount
            continue
        cost = amount * price
        bucket["priced_energy_kwh"] += amount
        bucket["cost"] += cost
        segment = {"price_per_kwh": price, "energy_kwh": amount, "cost": cost}
        if bucket["price_segments"] and bucket["price_segments"][-1]["price_per_kwh"] == price:
            bucket["price_segments"][-1]["energy_kwh"] += amount
            bucket["price_segments"][-1]["cost"] += cost
        else:
            bucket["price_segments"].append(segment)

    breakdown = []
    total_cost = 0.0
    priced_energy = 0.0
    unpriced_energy = 0.0
    for bucket in buckets.values():
        bucket["energy_kwh"] = round(bucket["energy_kwh"], 6)
        bucket["cost"] = round(bucket["cost"], 6)
        bucket["priced_energy_kwh"] = round(bucket["priced_energy_kwh"], 6)
        bucket["unpriced_energy_kwh"] = round(bucket["unpriced_energy_kwh"], 6)
        for segment in bucket["price_segments"]:
            segment["energy_kwh"] = round(segment["energy_kwh"], 6)
            segment["cost"] = round(segment["cost"], 6)
        prices = {item["price_per_kwh"] for item in bucket["price_segments"]}
        bucket["price_per_kwh"] = next(iter(prices)) if len(prices) == 1 else None
        total_cost += bucket["cost"]
        priced_energy += bucket["priced_energy_kwh"]
        unpriced_energy += bucket["unpriced_energy_kwh"]
        breakdown.append(bucket)

    return {
        "energy_kwh": round(energy_kwh, 6),
        "cost": round(total_cost, 6),
        "priced_energy_kwh": round(priced_energy, 6),
        "unpriced_energy_kwh": round(unpriced_energy, 6),
        "estimated": True,
        "method": "power" if use_power else "time_fallback",
        "breakdown": breakdown,
    }
