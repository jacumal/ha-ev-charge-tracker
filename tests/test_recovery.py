"""Pure tests for session recovery guards and source freshness."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from custom_components.ev_charge_tracker.coordinator import (
    _energy_delta,
    _session_recovery_action,
    _state_is_fresh,
    _state_updated_at_or_after,
    EVChargeCoordinator,
)


class SessionRecoveryGuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)

    def state(self, value="1", updated=None):
        return SimpleNamespace(
            state=value,
            last_updated=updated or self.now,
        )

    def test_recent_valid_state_is_fresh(self):
        self.assertTrue(_state_is_fresh(self.state(), self.now))

    def test_state_older_than_ten_minutes_is_stale(self):
        old = self.state(updated=self.now - timedelta(minutes=11))
        self.assertFalse(_state_is_fresh(old, self.now))

    def test_future_timestamp_is_rejected(self):
        future = self.state(updated=self.now + timedelta(seconds=1))
        self.assertFalse(_state_is_fresh(future, self.now))

    def test_unavailable_or_unknown_state_is_rejected(self):
        self.assertFalse(_state_is_fresh(self.state("unavailable"), self.now))
        self.assertFalse(_state_is_fresh(self.state("unknown"), self.now))

    def test_missing_state_or_timestamp_is_rejected(self):
        self.assertFalse(_state_is_fresh(None, self.now))
        self.assertFalse(
            _state_is_fresh(SimpleNamespace(state="1", last_updated=None), self.now)
        )

    def test_odometer_must_be_observed_at_or_after_charge_stop(self):
        stopped_at = self.now - timedelta(minutes=5)
        before = self.state(updated=stopped_at - timedelta(seconds=1))
        after = self.state(updated=stopped_at + timedelta(seconds=1))
        self.assertFalse(_state_updated_at_or_after(before, stopped_at))
        self.assertTrue(_state_updated_at_or_after(after, stopped_at))

    def test_source_diagnostic_clears_when_entity_recovers(self):
        coordinator = object.__new__(EVChargeCoordinator)
        coordinator.data = {
            "diagnostic": "Sesión iniciada",
            "diagnostic_before_source": "Sesión iniciada",
            "source_diagnostics": {},
        }
        coordinator._set_source_diagnostic("sensor.odometer")
        self.assertEqual(
            coordinator.data["diagnostic"],
            "Lectura no disponible: sensor.odometer",
        )
        coordinator._clear_source_diagnostic("sensor.odometer")
        self.assertEqual(coordinator.data["diagnostic"], "Sesión iniciada")
        self.assertEqual(coordinator.data["source_diagnostics"], {})

    def test_multiple_source_diagnostics_clear_independently(self):
        coordinator = object.__new__(EVChargeCoordinator)
        coordinator.data = {
            "diagnostic": "Sesión iniciada",
            "diagnostic_before_source": "Sesión iniciada",
            "source_diagnostics": {},
        }
        coordinator._set_source_diagnostic("sensor.odometer")
        coordinator._set_source_diagnostic("sensor.energy")
        coordinator._clear_source_diagnostic("sensor.odometer")
        self.assertEqual(
            coordinator.data["diagnostic"],
            "Lectura no disponible: sensor.energy",
        )
        coordinator._clear_source_diagnostic("sensor.energy")
        self.assertEqual(coordinator.data["diagnostic"], "Sesión iniciada")

    def test_meter_counter_reset_never_creates_negative_energy(self):
        self.assertIsNone(_energy_delta(12.5, 0.2))
        self.assertEqual(_energy_delta(12.5, 12.5), 0.0)
        self.assertAlmostEqual(_energy_delta(12.5, 13.1), 0.6)

    def test_recovery_matrix_preserves_session_when_charger_state_is_unknown(self):
        active = {"ended_at": None, "status": "charging"}
        pending = {"ended_at": "2026-11-20T08:00:00+00:00", "status": "pending_finalization"}
        for state in (None, "unknown", "unavailable"):
            with self.subTest(state=state):
                self.assertEqual(_session_recovery_action(state, active), "preserve")
                self.assertEqual(_session_recovery_action(state, pending), "preserve")
                self.assertEqual(_session_recovery_action(state, None), "preserve")

    def test_recovery_matrix_starts_only_when_on_and_no_session_exists(self):
        self.assertEqual(_session_recovery_action("on", None), "start")
        self.assertEqual(
            _session_recovery_action("on", {"ended_at": None}),
            "continue",
        )

    def test_recovery_matrix_resumes_pending_session_when_charging_returns(self):
        pending = {"ended_at": "2026-11-20T08:00:00+00:00"}
        self.assertEqual(_session_recovery_action("on", pending), "resume")

    def test_recovery_matrix_stops_active_session_when_charger_is_off(self):
        active = {"ended_at": None}
        self.assertEqual(_session_recovery_action("off", active), "stop")
        self.assertEqual(
            _session_recovery_action("off", {"ended_at": "2026-11-20T08:00:00+00:00"}),
            "idle",
        )


if __name__ == "__main__":
    unittest.main()
