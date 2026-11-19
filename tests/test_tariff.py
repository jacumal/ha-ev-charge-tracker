"""Tests for the tariff schedule engine."""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.ev_charge_tracker.tariff import (
    active_period,
    allocate_energy_by_time,
    validate_periods,
)


class TariffTests(unittest.TestCase):
    def setUp(self):
        self.periods = [
            {"name": "Valle", "start": "00:00", "end": "08:00", "price": 0.08},
            {"name": "Punta", "start": "08:00", "end": "24:00", "price": 0.20},
        ]

    def test_selects_period(self):
        self.assertEqual(
            active_period(datetime(2026, 11, 19, 7, 30), self.periods)["name"],
            "Valle",
        )
        self.assertEqual(
            active_period(datetime(2026, 11, 19, 8, 0), self.periods)["name"],
            "Punta",
        )

    def test_allocates_energy_across_boundary(self):
        result = allocate_energy_by_time(
            datetime(2026, 11, 19, 7, 0),
            datetime(2026, 11, 19, 9, 0),
            10.0,
            self.periods,
        )
        self.assertAlmostEqual(result["breakdown"][0]["energy_kwh"], 5.0)
        self.assertAlmostEqual(result["breakdown"][1]["energy_kwh"], 5.0)
        self.assertAlmostEqual(result["cost"], 1.4)
        self.assertTrue(result["estimated"])

    def test_detects_schedule_gap(self):
        broken = [
            {"name": "A", "start": "00:00", "end": "07:00", "price": 0.1},
            {"name": "B", "start": "08:00", "end": "24:00", "price": 0.2},
        ]
        self.assertTrue(any("huecos" in error for error in validate_periods(broken)))

    def test_full_day_period_accepts_24_hour_boundary(self):
        periods = [
            {"name": "Único", "start": "00:00", "end": "24:00", "price": 0.12}
        ]
        self.assertEqual(validate_periods(periods), [])
        self.assertEqual(
            active_period(datetime(2026, 11, 19, 23, 59), periods)["name"],
            "Único",
        )

    def test_overnight_period(self):
        periods = [
            {"name": "Noche", "start": "22:00", "end": "06:00", "price": 0.07},
            {"name": "Día", "start": "06:00", "end": "22:00", "price": 0.18},
        ]
        self.assertEqual(
            active_period(datetime(2026, 11, 19, 23, 0), periods)["name"],
            "Noche",
        )
        self.assertEqual(
            active_period(datetime(2026, 11, 20, 2, 0), periods)["name"],
            "Noche",
        )

    def test_detects_overlapping_periods(self):
        overlapping = [
            {"name": "A", "start": "00:00", "end": "12:00", "price": 0.1},
            {"name": "B", "start": "11:00", "end": "24:00", "price": 0.2},
        ]
        self.assertTrue(any("solapados" in error for error in validate_periods(overlapping)))

    def test_rejects_non_finite_price(self):
        invalid = [
            {"name": "Único", "start": "00:00", "end": "24:00", "price": float("nan")}
        ]
        self.assertTrue(any("finito" in error for error in validate_periods(invalid)))

    def test_rejects_empty_period_name(self):
        invalid = [
            {"name": " ", "start": "00:00", "end": "24:00", "price": 0.1}
        ]
        self.assertTrue(any("nombre" in error for error in validate_periods(invalid)))

    def test_dst_spring_forward_uses_real_elapsed_time(self):
        madrid = ZoneInfo("Europe/Madrid")
        periods = [
            {"name": "Único", "start": "00:00", "end": "24:00", "price": 0.1}
        ]
        result = allocate_energy_by_time(
            datetime(2026, 3, 29, 1, 30, tzinfo=madrid),
            datetime(2026, 3, 29, 3, 30, tzinfo=madrid),
            2.0,
            periods,
        )
        self.assertAlmostEqual(result["energy_kwh"], 2.0)
        self.assertAlmostEqual(result["cost"], 0.2)


if __name__ == "__main__":
    unittest.main()
