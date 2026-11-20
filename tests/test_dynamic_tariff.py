"""Tests for timestamped dynamic tariff prices."""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.ev_charge_tracker.power import allocate_energy_by_dynamic_price


class DynamicTariffPriceTests(unittest.TestCase):
    def setUp(self):
        self.zone = ZoneInfo("Europe/Madrid")
        self.periods = [
            {
                "name": "Valle", "start": "00:00", "end": "08:00",
                "price": 0.15, "price_entity": "sensor.price_valle",
            },
            {
                "name": "Punta", "start": "08:00", "end": "24:00",
                "price": 0.30, "price_entity": "sensor.price_punta",
            },
        ]
        self.start = datetime(2026, 11, 19, 7, 0, tzinfo=self.zone)
        self.end = datetime(2026, 11, 19, 9, 0, tzinfo=self.zone)

    def test_price_change_inside_period_is_applied_at_its_timestamp(self):
        samples = [
            {"at": self.start.isoformat(), "period": "Valle", "price": 0.10},
            {
                "at": datetime(2026, 11, 19, 7, 30, tzinfo=self.zone).isoformat(),
                "period": "Valle", "price": 0.20,
            },
            {"at": self.start.isoformat(), "period": "Punta", "price": 0.30},
        ]
        result = allocate_energy_by_dynamic_price(
            self.start, self.end, 4.0, self.periods, [], samples
        )
        by_period = {item["period"]: item for item in result["breakdown"]}
        self.assertAlmostEqual(by_period["Valle"]["energy_kwh"], 2.0)
        self.assertAlmostEqual(by_period["Valle"]["cost"], 0.30)
        self.assertEqual(len(by_period["Valle"]["price_segments"]), 2)
        self.assertAlmostEqual(by_period["Punta"]["energy_kwh"], 2.0)
        self.assertAlmostEqual(by_period["Punta"]["cost"], 0.60)
        self.assertAlmostEqual(result["cost"], 0.90)
        self.assertAlmostEqual(result["priced_energy_kwh"], 4.0)
        self.assertAlmostEqual(result["unpriced_energy_kwh"], 0.0)
        self.assertEqual(result["method"], "time_fallback")

    def test_unavailable_price_does_not_reuse_previous_price(self):
        samples = [
            {"at": self.start.isoformat(), "period": "Valle", "price": 0.10},
            {
                "at": datetime(2026, 11, 19, 7, 30, tzinfo=self.zone).isoformat(),
                "period": "Valle", "price": None,
            },
            {"at": self.start.isoformat(), "period": "Punta", "price": 0.30},
        ]
        result = allocate_energy_by_dynamic_price(
            self.start, self.end, 4.0, self.periods, [], samples
        )
        by_period = {item["period"]: item for item in result["breakdown"]}
        self.assertAlmostEqual(by_period["Valle"]["priced_energy_kwh"], 1.0)
        self.assertAlmostEqual(by_period["Valle"]["unpriced_energy_kwh"], 1.0)
        self.assertAlmostEqual(by_period["Valle"]["cost"], 0.10)
        self.assertAlmostEqual(result["priced_energy_kwh"], 3.0)
        self.assertAlmostEqual(result["unpriced_energy_kwh"], 1.0)
        self.assertAlmostEqual(result["cost"], 0.70)

    def test_missing_initial_dynamic_price_leaves_energy_unpriced(self):
        samples = [
            {"at": self.start.isoformat(), "period": "Punta", "price": 0.30},
        ]
        result = allocate_energy_by_dynamic_price(
            self.start, self.end, 4.0, self.periods, [], samples
        )
        by_period = {item["period"]: item for item in result["breakdown"]}
        self.assertAlmostEqual(by_period["Valle"]["unpriced_energy_kwh"], 2.0)
        self.assertAlmostEqual(by_period["Punta"]["priced_energy_kwh"], 2.0)

    def test_manual_period_price_still_works_without_sensor(self):
        periods = [
            {"name": "Único", "start": "00:00", "end": "24:00", "price": 0.12}
        ]
        result = allocate_energy_by_dynamic_price(
            self.start, self.end, 5.0, periods, [], []
        )
        self.assertAlmostEqual(result["cost"], 0.60)
        self.assertAlmostEqual(result["priced_energy_kwh"], 5.0)
        self.assertAlmostEqual(result["unpriced_energy_kwh"], 0.0)

    def test_power_profile_is_still_used_with_dynamic_prices(self):
        power = [
            {"at": self.start.isoformat(), "power_kw": 2.0},
            {"at": self.end.isoformat(), "power_kw": 2.0},
        ]
        prices = [
            {"at": self.start.isoformat(), "period": "Valle", "price": 0.10},
            {"at": self.start.isoformat(), "period": "Punta", "price": 0.20},
        ]
        result = allocate_energy_by_dynamic_price(
            self.start, self.end, 4.0, self.periods, power, prices
        )
        self.assertEqual(result["method"], "power")
        self.assertAlmostEqual(result["cost"], 0.60)


if __name__ == "__main__":
    unittest.main()
