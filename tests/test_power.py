"""Tests for power-based tariff allocation."""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.ev_charge_tracker.power import allocate_energy_by_power, allocate_energy_by_dynamic_price


class PowerAllocationTests(unittest.TestCase):
    def setUp(self):
        self.zone = ZoneInfo("Europe/Madrid")
        self.periods = [
            {"name": "Valle", "start": "00:00", "end": "08:00", "price": 0.08},
            {"name": "Punta", "start": "08:00", "end": "24:00", "price": 0.20},
        ]

    def test_power_profile_weights_energy_across_tariff_boundary(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 9, 0, tzinfo=self.zone)
        samples = [
            {"at": start.isoformat(), "power_kw": 3.0},
            {"at": datetime(2026, 11, 19, 7, 59, tzinfo=self.zone).isoformat(), "power_kw": 3.0},
            {"at": datetime(2026, 11, 19, 8, 0, tzinfo=self.zone).isoformat(), "power_kw": 9.0},
            {"at": end.isoformat(), "power_kw": 9.0},
        ]
        result = allocate_energy_by_power(start, end, 12.0, self.periods, samples)
        by_name = {item["period"]: item["energy_kwh"] for item in result["breakdown"]}
        self.assertAlmostEqual(by_name["Valle"], 3.0, places=1)
        self.assertAlmostEqual(by_name["Punta"], 9.0, places=1)
        self.assertAlmostEqual(sum(by_name.values()), 12.0, places=5)
        self.assertEqual(result["method"], "power")

    def test_meter_delta_remains_authoritative_when_power_integral_differs(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 9, 0, tzinfo=self.zone)
        samples = [
            {"at": start.isoformat(), "power_kw": 5.0},
            {"at": end.isoformat(), "power_kw": 5.0},
        ]
        result = allocate_energy_by_power(start, end, 7.25, self.periods, samples)
        self.assertAlmostEqual(sum(x["energy_kwh"] for x in result["breakdown"]), 7.25, places=5)

    def test_missing_power_uses_time_estimate(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 9, 0, tzinfo=self.zone)
        result = allocate_energy_by_power(start, end, 10.0, self.periods, [])
        self.assertEqual(result["method"], "time_fallback")
        self.assertAlmostEqual(sum(x["energy_kwh"] for x in result["breakdown"]), 10.0, places=5)

    def test_stale_power_samples_fall_back_to_time_estimate(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 9, 0, tzinfo=self.zone)
        samples = [{"at": start.isoformat(), "power_kw": 7.0}]
        result = allocate_energy_by_power(start, end, 4.0, self.periods, samples)
        self.assertEqual(result["method"], "time_fallback")
        self.assertAlmostEqual(sum(x["energy_kwh"] for x in result["breakdown"]), 4.0, places=5)

    def test_future_dated_power_sample_does_not_hide_stale_end_edge(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 9, 0, tzinfo=self.zone)
        samples = [
            {"at": start.isoformat(), "power_kw": 7.0},
            {"at": datetime(2026, 11, 19, 9, 10, tzinfo=self.zone).isoformat(), "power_kw": 7.0},
        ]
        result = allocate_energy_by_power(start, end, 4.0, self.periods, samples)
        self.assertEqual(result["method"], "time_fallback")
        self.assertAlmostEqual(sum(x["energy_kwh"] for x in result["breakdown"]), 4.0, places=5)

    def test_zero_power_falls_back_without_losing_meter_energy(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 9, 0, tzinfo=self.zone)
        samples = [{"at": start.isoformat(), "power_kw": 0.0}]
        result = allocate_energy_by_power(start, end, 3.0, self.periods, samples)
        self.assertEqual(result["method"], "time_fallback")
        self.assertAlmostEqual(sum(x["energy_kwh"] for x in result["breakdown"]), 3.0, places=5)

    def test_unavailable_dynamic_price_never_falls_back_to_manual_price(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 8, 0, tzinfo=self.zone)
        periods = [{
            "name": "Valle", "start": "00:00", "end": "24:00",
            "price": 0.08, "price_entity": "sensor.precio_valle",
        }]
        result = allocate_energy_by_dynamic_price(start, end, 2.0, periods, [], [
            {"at": start.isoformat(), "period": "Valle", "price": None},
        ])
        self.assertEqual(result["priced_energy_kwh"], 0)
        self.assertAlmostEqual(result["unpriced_energy_kwh"], 2.0)
        self.assertEqual(result["cost"], 0)

    def test_dynamic_price_change_is_applied_at_its_timestamp(self):
        start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        middle = datetime(2026, 11, 19, 7, 30, tzinfo=self.zone)
        end = datetime(2026, 11, 19, 8, 0, tzinfo=self.zone)
        periods = [{
            "name": "Valle", "start": "00:00", "end": "24:00",
            "price_entity": "sensor.precio_valle",
        }]
        result = allocate_energy_by_dynamic_price(start, end, 2.0, periods, [], [
            {"at": start.isoformat(), "period": "Valle", "price": 0.1},
            {"at": middle.isoformat(), "period": "Valle", "price": 0.2},
        ])
        self.assertAlmostEqual(result["cost"], 0.3, places=5)
        self.assertAlmostEqual(result["priced_energy_kwh"], 2.0, places=5)


if __name__ == "__main__":
    unittest.main()
