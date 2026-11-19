"""Tests for international unit conversion."""
import unittest

from custom_components.ev_charge_tracker.units import convert_unit, normalize_currency_code


class UnitConversionTests(unittest.TestCase):
    def test_energy_supports_wh_kwh_mwh_and_joules(self):
        self.assertAlmostEqual(convert_unit(1500, "energy", "Wh", "kWh"), 1.5)
        self.assertEqual(convert_unit(1, "energy", "MWh", "kWh"), 1000)
        self.assertAlmostEqual(convert_unit(3_600_000, "energy", "J", "kWh"), 1)

    def test_power_and_electrical_units(self):
        self.assertEqual(convert_unit(1500, "power", "W", "kW"), 1.5)
        self.assertEqual(convert_unit(230, "voltage", "V", "mV"), 230000)
        self.assertEqual(convert_unit(16, "current", "A", "mA"), 16000)

    def test_distance_supports_metric_imperial_and_small_units(self):
        self.assertAlmostEqual(convert_unit(1, "distance", "mi", "km"), 1.609344)
        self.assertAlmostEqual(convert_unit(1000, "distance", "m", "km"), 1)
        self.assertAlmostEqual(convert_unit(5280, "distance", "ft", "mi"), 1)

    def test_temperature_conversions(self):
        self.assertAlmostEqual(convert_unit(32, "temperature", "°F", "°C"), 0)
        self.assertAlmostEqual(convert_unit(0, "temperature", "°C", "K"), 273.15)

    def test_consumption_conversions(self):
        self.assertAlmostEqual(convert_unit(200, "consumption", "Wh/km", "kWh/100km"), 20)
        self.assertAlmostEqual(convert_unit(5, "consumption", "km/kWh", "kWh/100km"), 20)
        self.assertAlmostEqual(convert_unit(3.106856, "consumption", "mi/kWh", "kWh/100km"), 20, places=4)

    def test_unknown_units_are_rejected_instead_of_guessed(self):
        with self.assertRaises(ValueError):
            convert_unit(1, "energy", "widgets", "kWh")

    def test_currency_codes_are_normalized_but_not_exchange_converted(self):
        self.assertEqual(normalize_currency_code(" usd "), "USD")
        with self.assertRaises(ValueError):
            normalize_currency_code("EURO")


if __name__ == "__main__":
    unittest.main()
