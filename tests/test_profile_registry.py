"""Tests for normalized vehicle/charger identities and resource ownership."""

import unittest

from custom_components.ev_charge_tracker.profile_registry import (
    build_profile_identity,
    find_resource_conflicts,
    normalize_profile_id,
)


class ProfileRegistryTests(unittest.TestCase):
    def test_identity_is_stable_and_ascii_normalized(self):
        self.assertEqual(
            build_profile_identity("  Leapmotor C10  ", "V2C Garaje"),
            {"vehicle_id": "leapmotor_c10", "charger_id": "v2c_garaje"},
        )
        self.assertEqual(normalize_profile_id("Coche eléctrico"), "coche_electrico")

    def test_rejects_names_without_identifier_characters(self):
        with self.assertRaises(ValueError):
            normalize_profile_id(" 🚗 ")

    def test_allows_same_vehicle_with_different_chargers(self):
        profiles = [
            {"vehicle_id": "c10", "charger_id": "garage", "charging_entity": "binary_sensor.garage", "energy_entity": "sensor.garage_energy"}
        ]
        candidate = {
            "vehicle_id": "c10",
            "charger_id": "work",
            "charging_entity": "binary_sensor.work",
            "energy_entity": "sensor.work_energy",
        }
        self.assertEqual(find_resource_conflicts(candidate, profiles), set())

    def test_detects_shared_charging_and_energy_resources(self):
        profiles = [
            {"charging_entity": "binary_sensor.charging", "energy_entity": "sensor.energy"}
        ]
        candidate = {
            "charging_entity": "binary_sensor.charging",
            "energy_entity": "sensor.energy",
        }
        self.assertEqual(
            find_resource_conflicts(candidate, profiles),
            {"charging_entity", "energy_entity"},
        )

    def test_allows_shared_non_ownership_telemetry(self):
        profiles = [{"soc_entity": "sensor.car_soc", "odometer_entity": "sensor.car_odometer"}]
        candidate = {"soc_entity": "sensor.car_soc", "odometer_entity": "sensor.car_odometer"}
        self.assertEqual(find_resource_conflicts(candidate, profiles), set())


if __name__ == "__main__":
    unittest.main()
