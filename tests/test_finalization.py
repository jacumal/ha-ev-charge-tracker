"""Session finalization regression tests."""

import unittest

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
            "soc_end": None,
        }
        coordinator = self.make_coordinator(session)

        coordinator._finalize()

        self.assertIsNone(coordinator.data["session"])
        self.assertEqual(coordinator.data["status"], "idle")
        self.assertEqual(len(coordinator.data["history"]), 1)
        self.assertEqual(coordinator.data["latest"]["energy_kwh"], 12.5)
        self.assertEqual(coordinator.data["latest"]["cost"], 2.5)
        self.assertEqual(coordinator.data["latest"]["soc_end"], 77.0)
        self.assertEqual(
            coordinator.data["latest"]["session_id"],
            "2026-11-19T10:00:00+00:00",
        )

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


if __name__ == "__main__":
    unittest.main()
