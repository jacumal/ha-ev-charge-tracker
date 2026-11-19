"""Additional regression tests for sensor value handling."""

import unittest

from custom_components.ev_charge_tracker.coordinator import (
    _energy_delta,
    _normalize_energy,
    _number,
)


class SensorValueTests(unittest.TestCase):
    def test_number_rejects_unavailable_and_non_finite_values(self):
        for value in (None, "", "unknown", "unavailable", "none", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                self.assertIsNone(_number(value))

    def test_number_accepts_zero_and_decimal_values(self):
        self.assertEqual(_number("0"), 0.0)
        self.assertEqual(_number("18.75"), 18.75)

    def test_energy_counter_reset_never_produces_negative_delta(self):
        self.assertIsNone(_energy_delta(18.2, 0.0))
        self.assertIsNone(_energy_delta(18.2, 3.0))

    def test_energy_counter_unchanged_is_valid_zero_delta(self):
        self.assertEqual(_energy_delta(18.2, 18.2), 0.0)

    def test_wh_conversion_keeps_precision(self):
        self.assertAlmostEqual(_normalize_energy("12345.6", "Wh"), 12.3456)


if __name__ == "__main__":
    unittest.main()
