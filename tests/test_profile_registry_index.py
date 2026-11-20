"""Tests for the in-memory vehicle/charger/profile registry."""

from types import SimpleNamespace
import unittest

from custom_components.ev_charge_tracker.profile_registry import (
    build_profile_registry,
)


class ProfileRegistryIndexTests(unittest.TestCase):
    def entry(self, entry_id, data, options=None):
        return SimpleNamespace(
            entry_id=entry_id,
            data=data,
            options=options or {},
        )

    def test_indexes_multiple_profiles_for_one_vehicle(self):
        registry = build_profile_registry([
            self.entry("home", {
                "vehicle_id": "c10", "charger_id": "garage",
                "vehicle_name": "C10", "charger_name": "Garaje",
            }),
            self.entry("work", {
                "vehicle_id": "c10", "charger_id": "work",
                "vehicle_name": "C10", "charger_name": "Trabajo",
            }),
        ])
        self.assertEqual(set(registry["vehicles"]), {"c10"})
        self.assertEqual(
            set(registry["vehicles"]["c10"]["profile_ids"]), {"home", "work"}
        )
        self.assertEqual(set(registry["chargers"]), {"garage", "work"})
        self.assertEqual(len(registry["profiles"]), 2)

    def test_legacy_entries_get_fallback_ids_without_mutating_data(self):
        data = {
            "vehicle_name": "Coche eléctrico",
            "charger_name": "Punto garaje",
            "charging_entity": "binary_sensor.charge",
            "energy_entity": "sensor.energy",
        }
        registry = build_profile_registry([self.entry("legacy-1", data)])
        profile = registry["profiles"]["legacy-1"]
        self.assertEqual(profile["vehicle_id"], "coche_electrico")
        self.assertEqual(profile["charger_id"], "punto_garaje")
        self.assertTrue(profile["legacy"])
        self.assertNotIn("vehicle_id", data)
        self.assertNotIn("charger_id", data)

    def test_legacy_entry_without_names_uses_entry_id_fallback(self):
        registry = build_profile_registry([self.entry("old-entry-2", {})])
        profile = registry["profiles"]["old-entry-2"]
        self.assertEqual(profile["vehicle_id"], "legacy_vehicle_old_entry_2")
        self.assertEqual(profile["charger_id"], "legacy_charger_old_entry_2")

    def test_options_override_config_data_for_sensor_mapping(self):
        registry = build_profile_registry([
            self.entry(
                "profile-1",
                {"vehicle_id": "car", "charger_id": "charger",
                 "charging_entity": "binary_sensor.old"},
                {"charging_entity": "binary_sensor.new"},
            )
        ])
        self.assertEqual(
            registry["profiles"]["profile-1"]["charging_entity"],
            "binary_sensor.new",
        )

    def test_detects_duplicate_charging_and_energy_ownership(self):
        registry = build_profile_registry([
            self.entry("one", {
                "vehicle_id": "car1", "charger_id": "charger1",
                "charging_entity": "binary_sensor.shared",
                "energy_entity": "sensor.shared",
            }),
            self.entry("two", {
                "vehicle_id": "car2", "charger_id": "charger2",
                "charging_entity": "binary_sensor.shared",
                "energy_entity": "sensor.shared",
            }),
        ])
        self.assertEqual(
            registry["conflicts"]["charging_entity:binary_sensor.shared"],
            ["one", "two"],
        )
        self.assertEqual(
            registry["conflicts"]["energy_entity:sensor.shared"],
            ["one", "two"],
        )

    def test_shared_vehicle_telemetry_is_not_a_registry_conflict(self):
        registry = build_profile_registry([
            self.entry("one", {
                "vehicle_id": "car", "charger_id": "home",
                "soc_entity": "sensor.car_soc",
                "odometer_entity": "sensor.car_odometer",
            }),
            self.entry("two", {
                "vehicle_id": "car", "charger_id": "work",
                "soc_entity": "sensor.car_soc",
                "odometer_entity": "sensor.car_odometer",
            }),
        ])
        self.assertEqual(registry["conflicts"], {})


if __name__ == "__main__":
    unittest.main()
