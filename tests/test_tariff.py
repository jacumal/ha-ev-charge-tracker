"""Tests for the tariff schedule engine."""

import unittest
from datetime import datetime

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


if __name__ == "__main__":
    unittest.main()
