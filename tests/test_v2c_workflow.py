"""Regression tests for the V2C odometer/SOC-max workflow."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from custom_components.ev_charge_tracker.coordinator import EVChargeCoordinator
from custom_components.ev_charge_tracker.const import (
    CONF_ENERGY_ENTITY,
    CONF_SOC_ENTITY,
)


class V2CWorkflowTests(unittest.TestCase):
    def make_coordinator(self, session, config, states=None):
        coordinator = object.__new__(EVChargeCoordinator)
        coordinator.config = config
        coordinator.data = {
            "status": session.get("status", "charging"),
            "session": session,
            "history": [],
            "latest": None,
            "diagnostic": "",
        }
        coordinator.hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda entity_id: (states or {}).get(entity_id))
        )
        coordinator._allocate_tariff_delta = Mock()
        return coordinator

    def test_energy_counter_reset_establishes_new_baseline_without_losing_total(self):
        config = {CONF_ENERGY_ENTITY: "sensor.evse_energy"}
        session = {
            "status": "charging",
            "energy_kwh": 32.59,
            "energy_valid": True,
            "last_energy_sample_kwh": 32.59,
            "last_energy_sample_at": "2026-11-28T08:00:00+00:00",
            "tariff_breakdown": {},
            "power_samples": [],
        }
        state = SimpleNamespace(
            state="0.20",
            attributes={"unit_of_measurement": "kWh"},
        )
        coordinator = self.make_coordinator(session, config, {"sensor.evse_energy": state})
        coordinator._read_energy_kwh = Mock(side_effect=[0.20, 0.70])

        coordinator._capture_measurements("sensor.evse_energy", "0.20")
        self.assertEqual(session["energy_kwh"], 32.59)
        self.assertEqual(session["last_energy_sample_kwh"], 0.20)
        self.assertIn("Contador reiniciado", coordinator.data["diagnostic"])

        coordinator._capture_measurements("sensor.evse_energy", "0.70")
        self.assertEqual(session["energy_kwh"], 33.09)
        self.assertTrue(session["energy_valid"])
        coordinator._allocate_tariff_delta.assert_called_once()

    def test_soc_max_continues_to_update_while_waiting_for_odometer(self):
        config = {CONF_SOC_ENTITY: "sensor.vehicle_soc"}
        session = {
            "status": "pending_finalization",
            "ended_at": "2026-11-28T08:00:00+00:00",
            "soc_max": 90.0,
            "soc_last": 90.0,
        }
        state = SimpleNamespace(
            state="92.5",
            attributes={"unit_of_measurement": "%"},
        )
        coordinator = self.make_coordinator(session, config, {"sensor.vehicle_soc": state})

        coordinator._capture_measurements("sensor.vehicle_soc", "92.5")

        self.assertEqual(session["soc_max"], 92.5)
        self.assertEqual(session["soc_last"], 92.5)

    def test_soc_max_ignores_invalid_or_lower_values_while_pending(self):
        config = {CONF_SOC_ENTITY: "sensor.vehicle_soc"}
        session = {
            "status": "pending_finalization",
            "ended_at": "2026-11-28T08:00:00+00:00",
            "soc_max": 92.5,
            "soc_last": 92.5,
        }
        state = SimpleNamespace(
            state="91.0",
            attributes={"unit_of_measurement": "%"},
        )
        coordinator = self.make_coordinator(session, config, {"sensor.vehicle_soc": state})

        coordinator._capture_measurements("sensor.vehicle_soc", "91.0")

        self.assertEqual(session["soc_max"], 92.5)
        self.assertEqual(session["soc_last"], 91.0)

    def test_v2c_pending_session_is_not_finalized_without_odometer_increase(self):
        from custom_components.ev_charge_tracker.const import (
            CONF_CHARGING_ENTITY, CONF_FINALIZATION, CONF_ODOMETER_ENTITY,
            FINALIZE_ODOMETER,
        )
        stopped = datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc)
        charger = SimpleNamespace(state="off")
        odometer = SimpleNamespace(
            state="12000",
            last_updated=stopped.replace(minute=1),
            attributes={"unit_of_measurement": "km"},
        )
        session = {
            "status": "pending_finalization",
            "ended_at": stopped.isoformat(),
            "odometer_start_km": 12000.0,
            "energy_valid": True,
        }
        config = {
            CONF_CHARGING_ENTITY: "binary_sensor.charger",
            CONF_ODOMETER_ENTITY: "sensor.odometer",
            CONF_FINALIZATION: FINALIZE_ODOMETER,
        }
        coordinator = self.make_coordinator(
            session,
            config,
            {"binary_sensor.charger": charger, "sensor.odometer": odometer},
        )
        coordinator._read_odometer = Mock(return_value=12000.0)
        coordinator._finalize = Mock()

        coordinator._try_finalize()

        coordinator._finalize.assert_not_called()
        self.assertEqual(coordinator.data["session"], session)

    def test_v2c_finalizes_only_after_fresh_odometer_increase_and_valid_energy(self):
        from custom_components.ev_charge_tracker.const import (
            CONF_CHARGING_ENTITY, CONF_FINALIZATION, CONF_ODOMETER_ENTITY,
            FINALIZE_ODOMETER,
        )
        stopped = datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc)
        charger = SimpleNamespace(state="off")
        odometer = SimpleNamespace(
            state="12001",
            last_updated=stopped.replace(minute=1),
            attributes={"unit_of_measurement": "km"},
        )
        session = {
            "status": "pending_finalization",
            "ended_at": stopped.isoformat(),
            "odometer_start_km": 12000.0,
            "energy_valid": True,
        }
        config = {
            CONF_CHARGING_ENTITY: "binary_sensor.charger",
            CONF_ODOMETER_ENTITY: "sensor.odometer",
            CONF_FINALIZATION: FINALIZE_ODOMETER,
        }
        coordinator = self.make_coordinator(
            session,
            config,
            {"binary_sensor.charger": charger, "sensor.odometer": odometer},
        )
        coordinator._read_odometer = Mock(return_value=12001.0)
        coordinator._finalize = Mock()

        coordinator._try_finalize()

        coordinator._finalize.assert_called_once()
        self.assertEqual(session["odometer_end_km"], 12001.0)


if __name__ == "__main__":
    unittest.main()
