"""Unit tests for energy counter normalization and deltas."""

import unittest

from custom_components.ev_charge_tracker.coordinator import (
    _energy_delta,
    _normalize_energy,
)


class EnergyCounterTests(unittest.TestCase):
    def test_normalizes_kwh(self):
        self.assertEqual(_normalize_energy("12.345", "kWh"), 12.345)

    def test_normalizes_wh(self):
        self.assertEqual(_normalize_energy("1250", "Wh"), 1.25)

    def test_rejects_unknown_values_and_units(self):
        self.assertIsNone(_normalize_energy("unavailable", "kWh"))
        self.assertIsNone(_normalize_energy("12", "W"))
        self.assertIsNone(_normalize_energy("-1", "kWh"))

    def test_cumulative_counter_counts_only_increase(self):
        self.assertAlmostEqual(_energy_delta(1234.5, 1236.0), 1.5)

    def test_counter_reset_requires_new_baseline(self):
        self.assertIsNone(_energy_delta(1236.0, 0.0))

    def test_first_sample_is_not_an_implicit_delta(self):
        self.assertIsNone(_energy_delta(None, 4.2))


if __name__ == "__main__":
    unittest.main()
