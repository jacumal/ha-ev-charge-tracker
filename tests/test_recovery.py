"""Pure tests for session recovery guards and source freshness."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from custom_components.ev_charge_tracker.coordinator import (
    _energy_delta,
    _state_is_fresh,
    _state_updated_at_or_after,
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

    def test_meter_counter_reset_never_creates_negative_energy(self):
        self.assertIsNone(_energy_delta(12.5, 0.2))
        self.assertEqual(_energy_delta(12.5, 12.5), 0.0)
        self.assertAlmostEqual(_energy_delta(12.5, 13.1), 0.6)


if __name__ == "__main__":
    unittest.main()
