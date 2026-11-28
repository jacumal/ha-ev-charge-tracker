"""Session finalization regression tests."""

import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from custom_components.ev_charge_tracker.coordinator import EVChargeCoordinator


class SessionFinalizationTests(unittest.TestCase):
    def make_coordinator(self, session):
        coordinator = object.__new__(EVChargeCoordinator)
        coordinator.data = {
            "status": "pending_finalization",
            "session": session,
            "latest": None,
            "history": [],
            "diagnostic": "Carga pendiente",
        }
        return coordinator

    def test_finalize_adds_one_history_record_and_clears_active_session(self):
        session = {
            "started_at": "2026-11-19T10:00:00+00:00",
            "ended_at": "2026-11-19T11:00:00+00:00",
            "status": "pending_finalization",
            "energy_kwh": 12.5,
            "energy_valid": True,
            "price_per_kwh": 0.2,
            "cost_complete": True,
            "tariff_breakdown": {},
            "soc_max": 80.0,
            "soc_last": 77.0,
            "soc_last_at": "2026-11-19T10:59:00+00:00",
            "soc_end": None,
        }
        coordinator = self.make_coordinator(session)

        coordinator._finalize()

        self.assertIsNone(coordinator.data["session"])
        self.assertEqual(coordinator.data["status"], "idle")
        self.assertEqual(len(coordinator.data["history"]), 1)
        self.assertEqual(coordinator.data["latest"]["energy_kwh"], 12.5)
        self.assertEqual(coordinator.data["latest"]["cost"], 2.5)
        self.assertEqual(coordinator.data["latest"]["soc_end"], 80.0)
        self.assertEqual(
            coordinator.data["latest"]["session_id"],
            "2026-11-19T10:00:00+00:00",
        )

    def test_odometer_workflow_uses_maximum_soc_not_last_stale_sample(self):
        coordinator = self.make_coordinator({
            "started_at": "2026-11-19T10:00:00+00:00",
            "ended_at": "2026-11-19T11:00:00+00:00",
            "energy_kwh": 8.0,
            "energy_valid": True,
            "price_per_kwh": 0.2,
            "cost_complete": True,
            "tariff_breakdown": {},
            "soc_max": 91.5,
            "soc_last": 84.0,
            "soc_last_at": "2026-11-19T10:20:00+00:00",
        })

        coordinator.config = {}
        coordinator._finalize()

        self.assertEqual(coordinator.data["latest"]["soc_end"], 91.5)

    def test_soc_reported_during_finalization_grace_is_saved(self):
        coordinator = self.make_coordinator({
            "started_at": "2026-11-19T10:00:00+00:00",
            "ended_at": "2026-11-19T11:00:00+00:00",
            "energy_kwh": 3.0,
            "energy_valid": True,
            "price_per_kwh": 0.1,
            "cost_complete": True,
            "tariff_breakdown": {},
            "soc_last": 85.0,
            "soc_last_at": "2026-11-19T11:02:00+00:00",
        })

        coordinator._finalize()

        self.assertEqual(coordinator.data["latest"]["soc_end"], 85.0)

    def test_stale_final_soc_is_not_saved(self):
        coordinator = self.make_coordinator({
            "started_at": "2026-11-19T10:00:00+00:00",
            "ended_at": "2026-11-19T11:00:00+00:00",
            "energy_kwh": 3.0,
            "energy_valid": True,
            "price_per_kwh": 0.1,
            "cost_complete": True,
            "tariff_breakdown": {},
            "soc_last": 84.0,
            "soc_last_at": "2026-11-19T10:40:00+00:00",
        })

        coordinator._finalize()

        self.assertIsNone(coordinator.data["latest"]["soc_end"])

    def test_repeated_finalize_does_not_duplicate_history(self):
        coordinator = self.make_coordinator({
            "started_at": "2026-11-19T10:00:00+00:00",
            "ended_at": "2026-11-19T11:00:00+00:00",
            "energy_kwh": 3.0,
            "energy_valid": True,
            "price_per_kwh": 0.1,
            "cost_complete": True,
            "tariff_breakdown": {},
        })

        coordinator._finalize()
        first_record = coordinator.data["latest"]
        coordinator._finalize()

        self.assertEqual(len(coordinator.data["history"]), 1)
        self.assertIs(coordinator.data["latest"], first_record)

    def test_partial_cost_keeps_known_amount_without_claiming_full_total(self):
        coordinator = self.make_coordinator({
            "started_at": "2026-11-19T10:00:00+00:00",
            "ended_at": "2026-11-19T11:00:00+00:00",
            "energy_kwh": 10.0,
            "energy_valid": True,
            "price_per_kwh": None,
            "cost_complete": False,
            "priced_energy_kwh": 5.0,
            "unpriced_energy_kwh": 5.0,
            "tariff_breakdown": {
                "Known period": {
                    "energy_kwh": 5.0,
                    "cost": 0.5,
                    "price_per_kwh": 0.1,
                }
            },
            "currency": "EUR",
        })

        coordinator._finalize()

        record = coordinator.data["latest"]
        self.assertIsNone(record["cost"])
        self.assertEqual(record["known_cost"], 0.5)
        self.assertEqual(record["cost_status"], "partial")
        self.assertEqual(record["priced_energy_kwh"], 5.0)
        self.assertEqual(record["unpriced_energy_kwh"], 5.0)
        self.assertEqual(record["currency"], "EUR")

    def test_missing_energy_is_not_fabricated_as_zero(self):
        coordinator = self.make_coordinator({
            "started_at": "2026-11-19T10:00:00+00:00",
            "ended_at": "2026-11-19T11:00:00+00:00",
            "energy_kwh": 0.0,
            "energy_valid": False,
            "price_per_kwh": 0.2,
            "cost_complete": True,
            "tariff_breakdown": {},
        })

        coordinator._finalize()

        record = coordinator.data["latest"]
        self.assertIsNone(record["cost"])
        self.assertFalse(record["energy_valid"])
        self.assertEqual(record["energy_kwh"], 0.0)
        self.assertEqual(len(coordinator.data["history"]), 1)


class FinalizationStrategyTests(unittest.TestCase):
    def setUp(self):
        from datetime import datetime, timezone
        from custom_components.ev_charge_tracker import coordinator as coordinator_module
        from custom_components.ev_charge_tracker.const import (
            CONF_CHARGING_ENTITY, CONF_FINALIZATION, CONF_ODOMETER_ENTITY,
            FINALIZE_IMMEDIATE, FINALIZE_MANUAL, FINALIZE_ODOMETER,
        )
        self.module = coordinator_module
        self.Mock = Mock
        self.now = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
        self.stopped_at = self.now - timedelta(minutes=2)
        self.config_keys = (CONF_CHARGING_ENTITY, CONF_FINALIZATION, CONF_ODOMETER_ENTITY)
        self.strategies = (FINALIZE_IMMEDIATE, FINALIZE_MANUAL, FINALIZE_ODOMETER)
        self.coordinator = object.__new__(EVChargeCoordinator)
        self.coordinator.config = {
            CONF_CHARGING_ENTITY: "binary_sensor.charger",
            CONF_ODOMETER_ENTITY: "sensor.odometer",
            CONF_FINALIZATION: FINALIZE_IMMEDIATE,
        }
        self.coordinator.data = {
            "session": {
                "ended_at": self.stopped_at.isoformat(),
                "energy_valid": True,
                "odometer_start_km": 100.0,
            },
            "diagnostic": "",
        }
        self.coordinator.hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda entity_id: SimpleNamespace(state="off"))
        )
        self.coordinator._finalize = Mock()
        self.coordinator._read_odometer = Mock(return_value=101.0)

    def test_immediate_strategy_waits_for_post_stop_grace_period(self):
        from datetime import timedelta
        with patch.object(self.module.dt_util, "utcnow", return_value=self.stopped_at + timedelta(seconds=30)):
            self.coordinator._try_finalize()
        self.coordinator._finalize.assert_not_called()
        self.assertIn("esperando lecturas finales", self.coordinator.data["diagnostic"])

    def test_immediate_strategy_finalizes_after_grace_with_valid_energy(self):
        with patch.object(self.module.dt_util, "utcnow", return_value=self.now):
            self.coordinator._try_finalize()
        self.coordinator._finalize.assert_called_once()

    def test_manual_strategy_never_auto_finalizes(self):
        from custom_components.ev_charge_tracker.const import CONF_FINALIZATION, FINALIZE_MANUAL
        self.coordinator.config[CONF_FINALIZATION] = FINALIZE_MANUAL
        self.coordinator._try_finalize()
        self.coordinator._finalize.assert_not_called()
        self.assertEqual(self.coordinator.data["diagnostic"], "Carga pendiente de confirmación manual")

    def test_odometer_strategy_requires_post_stop_observation(self):
        from datetime import timedelta
        from custom_components.ev_charge_tracker.const import CONF_FINALIZATION, FINALIZE_ODOMETER
        self.coordinator.config[CONF_FINALIZATION] = FINALIZE_ODOMETER
        old_state = SimpleNamespace(last_updated=self.stopped_at - timedelta(seconds=1))
        self.coordinator.hass.states.get = lambda entity_id: (SimpleNamespace(state="off") if entity_id == "binary_sensor.charger" else old_state)
        self.coordinator._try_finalize()
        self.coordinator._finalize.assert_not_called()

    def test_odometer_strategy_finalizes_with_increased_fresh_reading_and_energy(self):
        from datetime import timedelta
        from custom_components.ev_charge_tracker.const import CONF_FINALIZATION, FINALIZE_ODOMETER
        self.coordinator.config[CONF_FINALIZATION] = FINALIZE_ODOMETER
        fresh_state = SimpleNamespace(last_updated=self.stopped_at + timedelta(seconds=1))
        self.coordinator.hass.states.get = lambda entity_id: (SimpleNamespace(state="off") if entity_id == "binary_sensor.charger" else fresh_state)
        self.coordinator._try_finalize()
        self.coordinator._finalize.assert_called_once()

    def test_odometer_strategy_does_not_finalize_without_energy(self):
        from datetime import timedelta
        from custom_components.ev_charge_tracker.const import CONF_FINALIZATION, FINALIZE_ODOMETER
        self.coordinator.config[CONF_FINALIZATION] = FINALIZE_ODOMETER
        self.coordinator.data["session"]["energy_valid"] = False
        fresh_state = SimpleNamespace(last_updated=self.stopped_at + timedelta(seconds=1))
        self.coordinator.hass.states.get = lambda entity_id: (
            SimpleNamespace(state="off")
            if entity_id == "binary_sensor.charger"
            else fresh_state
        )
        self.coordinator._try_finalize()
        self.coordinator._finalize.assert_not_called()
        self.assertIn("falta una lectura válida de energía", self.coordinator.data["diagnostic"])


if __name__ == "__main__":
    unittest.main()
