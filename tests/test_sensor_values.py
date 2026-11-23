"""Additional regression tests for sensor value handling."""

import unittest
from types import SimpleNamespace

from custom_components.ev_charge_tracker.sensor import EVChargeCostSensor

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

    def test_live_cost_sensor_exposes_known_cost_during_charging(self):
        sensor = object.__new__(EVChargeCostSensor)
        sensor.coordinator = SimpleNamespace(
            data={"session": {
                "status": "charging", "energy_kwh": 10.0, "energy_valid": True,
                "price_per_kwh": 0.2, "cost_complete": True,
                "priced_energy_kwh": 10.0, "tariff_breakdown": {},
            }, "latest": None},
            config={"currency": "EUR"},
        )
        self.assertEqual(sensor.native_value, 2.0)
        self.assertEqual(sensor.extra_state_attributes["cost_status"], "in_progress")

    def test_live_partial_cost_is_not_reported_as_complete_total(self):
        sensor = object.__new__(EVChargeCostSensor)
        sensor.coordinator = SimpleNamespace(
            data={"session": {
                "status": "charging", "energy_kwh": 10.0, "energy_valid": True,
                "cost_complete": False, "priced_energy_kwh": 5.0,
                "unpriced_energy_kwh": 5.0,
                "tariff_breakdown": {"Known": {"energy_kwh": 5.0, "cost": 0.5}},
            }, "latest": None},
            config={"currency": "EUR"},
        )
        self.assertIsNone(sensor.native_value)
        self.assertEqual(sensor.extra_state_attributes["known_cost"], 0.5)
        self.assertEqual(sensor.extra_state_attributes["cost_status"], "partial")


    def test_history_sensor_exposes_evse_energy_source_diagnostics(self):
        from datetime import datetime, timezone
        from custom_components.ev_charge_tracker.sensor import EVChargeHistorySensor

        state = SimpleNamespace(
            state="unavailable",
            attributes={"unit_of_measurement": "kWh"},
            last_updated=datetime.now(timezone.utc),
        )
        sensor = object.__new__(EVChargeHistorySensor)
        sensor.coordinator = SimpleNamespace(
            config={"energy_entity": "sensor.evse_energy"},
            hass=SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: state)),
        )
        diagnostic = sensor._energy_source_diagnostic()
        self.assertEqual(diagnostic["energy_source_entity"], "sensor.evse_energy")
        self.assertEqual(diagnostic["energy_source_status"], "unavailable_state")
        self.assertEqual(diagnostic["energy_source_unit"], "kWh")



    def test_history_sensor_marks_valid_fresh_evse_energy_source(self):
        from datetime import datetime, timezone
        from custom_components.ev_charge_tracker.sensor import EVChargeHistorySensor

        state = SimpleNamespace(
            state="12500",
            attributes={"unit_of_measurement": "Wh"},
            last_updated=datetime.now(timezone.utc),
        )
        sensor = object.__new__(EVChargeHistorySensor)
        sensor.coordinator = SimpleNamespace(
            config={"energy_entity": "sensor.evse_energy"},
            hass=SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: state)),
        )
        diagnostic = sensor._energy_source_diagnostic()
        self.assertEqual(diagnostic["energy_source_status"], "valid")
        self.assertEqual(diagnostic["energy_source_unit"], "Wh")
        self.assertLessEqual(diagnostic["energy_source_age_seconds"], 1)

    def test_history_sensor_reports_missing_evse_entity(self):
        from custom_components.ev_charge_tracker.sensor import EVChargeHistorySensor

        sensor = object.__new__(EVChargeHistorySensor)
        sensor.coordinator = SimpleNamespace(
            config={"energy_entity": "sensor.evse_energy"},
            hass=SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: None)),
        )
        self.assertEqual(sensor._energy_source_diagnostic()["energy_source_status"], "missing_entity")



if __name__ == "__main__":
    unittest.main()
