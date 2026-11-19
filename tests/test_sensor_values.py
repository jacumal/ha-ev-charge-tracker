"""Additional regression tests for sensor value handling."""

import unittest

from custom_components.ev_charge_tracker.coordinator import (
    _energy_delta,
    _normalize_energy,
    _normalize_odometer,
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

    def test_odometer_prefers_explicit_kilometer_sensor_unit(self):
        self.assertEqual(_normalize_odometer(100, "km", "mi"), 100)

    def test_odometer_converts_explicit_mile_sensor_unit(self):
        self.assertAlmostEqual(_normalize_odometer(100, "mi", "km"), 160.9344)

    def test_odometer_uses_configured_unit_when_sensor_unit_is_missing(self):
        self.assertAlmostEqual(_normalize_odometer(100, "", "mi"), 160.9344)

    def test_odometer_rejects_negative_and_missing_values(self):
        self.assertIsNone(_normalize_odometer(-1, "km"))
        self.assertIsNone(_normalize_odometer(None, "km"))


if __name__ == "__main__":
    unittest.main()
