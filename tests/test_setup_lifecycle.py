"""Config-entry lifecycle cleanup tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_components.ev_charge_tracker import DOMAIN
import custom_components.ev_charge_tracker as integration


class ConfigEntryLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.entry = SimpleNamespace(
            entry_id="profile-1",
            data={},
            options={},
            add_update_listener=Mock(return_value="listener"),
            async_on_unload=Mock(),
        )
        self.hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(
                async_entries=Mock(return_value=[]),
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
                async_reload=AsyncMock(),
            ),
        )
        self.coordinator = Mock()
        self.coordinator.async_setup = AsyncMock()
        self.coordinator.async_config_entry_first_refresh = AsyncMock()
        self.coordinator.async_shutdown = AsyncMock()

    async def test_first_refresh_failure_shuts_down_coordinator(self):
        self.coordinator.async_config_entry_first_refresh.side_effect = RuntimeError(
            "first refresh failed"
        )
        with patch.object(integration, "EVChargeCoordinator", return_value=self.coordinator):
            with self.assertRaisesRegex(RuntimeError, "first refresh failed"):
                await integration.async_setup_entry(self.hass, self.entry)

        self.coordinator.async_shutdown.assert_awaited_once()
        self.assertNotIn(self.entry.entry_id, self.hass.data[DOMAIN])

    async def test_platform_setup_failure_removes_profile_and_shuts_down(self):
        self.hass.config_entries.async_forward_entry_setups.side_effect = RuntimeError(
            "platform setup failed"
        )
        with patch.object(integration, "EVChargeCoordinator", return_value=self.coordinator):
            with self.assertRaisesRegex(RuntimeError, "platform setup failed"):
                await integration.async_setup_entry(self.hass, self.entry)

        self.hass.config_entries.async_unload_platforms.assert_awaited_once_with(
            self.entry, integration.PLATFORMS
        )
        self.coordinator.async_shutdown.assert_awaited_once()
        self.assertNotIn(self.entry.entry_id, self.hass.data[DOMAIN])

    async def test_platform_cleanup_failure_preserves_original_setup_error(self):
        self.hass.config_entries.async_forward_entry_setups.side_effect = RuntimeError(
            "platform setup failed"
        )
        self.hass.config_entries.async_unload_platforms.side_effect = RuntimeError(
            "platform cleanup failed"
        )
        with patch.object(integration, "EVChargeCoordinator", return_value=self.coordinator):
            with self.assertRaisesRegex(RuntimeError, "platform setup failed"):
                await integration.async_setup_entry(self.hass, self.entry)

        self.hass.config_entries.async_unload_platforms.assert_awaited_once_with(
            self.entry, integration.PLATFORMS
        )
        self.coordinator.async_shutdown.assert_awaited_once()
        self.assertNotIn(self.entry.entry_id, self.hass.data[DOMAIN])

    async def test_successful_setup_keeps_coordinator_registered(self):
        with patch.object(integration, "EVChargeCoordinator", return_value=self.coordinator):
            result = await integration.async_setup_entry(self.hass, self.entry)

        self.assertTrue(result)
        self.assertIs(self.hass.data[DOMAIN][self.entry.entry_id], self.coordinator)
        self.coordinator.async_shutdown.assert_not_awaited()
        self.entry.async_on_unload.assert_called_once()


    async def test_unload_entry_shuts_down_and_removes_profile(self):
        self.hass.data[DOMAIN] = {"profile-1": self.coordinator}
        result = await integration.async_unload_entry(self.hass, self.entry)

        self.assertTrue(result)
        self.hass.config_entries.async_unload_platforms.assert_awaited_once_with(
            self.entry, integration.PLATFORMS
        )
        self.coordinator.async_shutdown.assert_awaited_once()
        self.assertNotIn(self.entry.entry_id, self.hass.data[DOMAIN])

    async def test_failed_platform_unload_keeps_coordinator_registered(self):
        self.hass.data[DOMAIN] = {"profile-1": self.coordinator}
        self.hass.config_entries.async_unload_platforms.return_value = False

        result = await integration.async_unload_entry(self.hass, self.entry)

        self.assertFalse(result)
        self.coordinator.async_shutdown.assert_not_awaited()
        self.assertIs(self.hass.data[DOMAIN][self.entry.entry_id], self.coordinator)

    async def test_restart_restores_pending_session_and_resumes_when_charger_is_on(self):
        from datetime import datetime, timezone
        import custom_components.ev_charge_tracker.coordinator as coordinator_module
        from custom_components.ev_charge_tracker.const import (
            CONF_CHARGING_ENTITY, CONF_ENERGY_ENTITY, CONF_FINALIZATION,
            FINALIZE_IMMEDIATE,
        )

        restored_session = {
            "started_at": "2026-11-19T08:00:00+00:00",
            "ended_at": "2026-11-19T09:00:00+00:00",
            "status": "pending_finalization",
            "energy_kwh": 12.4,
            "energy_valid": True,
        }
        coordinator = object.__new__(coordinator_module.EVChargeCoordinator)
        coordinator.store = SimpleNamespace(async_load=AsyncMock(return_value={
            "status": "pending_finalization",
            "session": restored_session,
            "latest": None,
            "history": [{"session_id": "previous"}],
            "diagnostic": "restored",
        }))
        coordinator.data = {
            "status": "idle", "session": None, "latest": None,
            "history": [], "diagnostic": "",
        }
        coordinator.config = {
            CONF_CHARGING_ENTITY: "binary_sensor.charger",
            CONF_ENERGY_ENTITY: "sensor.energy",
            CONF_FINALIZATION: FINALIZE_IMMEDIATE,
        }
        coordinator.hass = SimpleNamespace(
            states=SimpleNamespace(get=Mock(return_value=SimpleNamespace(state="on")))
        )
        coordinator._unsub = []
        coordinator._async_save = AsyncMock()
        coordinator._capture_initial_tariff_prices = Mock()
        unsubscribe = Mock()

        with patch.object(
            coordinator_module, "async_track_state_change_event",
            return_value=unsubscribe,
        ):
            await coordinator.async_setup()

        self.assertIs(coordinator.data["session"], restored_session)
        self.assertIsNone(restored_session["ended_at"])
        self.assertEqual(restored_session["status"], "charging")
        self.assertEqual(coordinator.data["status"], "charging")
        self.assertEqual(coordinator.data["history"][0]["session_id"], "previous")
        coordinator._async_save.assert_awaited_once()
        coordinator._capture_initial_tariff_prices.assert_called_once()
        self.assertEqual(coordinator._unsub, [unsubscribe])

    async def test_restart_with_unknown_charger_state_preserves_restored_session(self):
        import custom_components.ev_charge_tracker.coordinator as coordinator_module
        from custom_components.ev_charge_tracker.const import (
            CONF_CHARGING_ENTITY, CONF_ENERGY_ENTITY,
        )

        restored_session = {
            "started_at": "2026-11-19T08:00:00+00:00",
            "ended_at": None,
            "status": "charging",
        }
        coordinator = object.__new__(coordinator_module.EVChargeCoordinator)
        coordinator.store = SimpleNamespace(async_load=AsyncMock(return_value={
            "status": "charging",
            "session": restored_session,
            "latest": None,
            "history": [],
            "diagnostic": "restored",
        }))
        coordinator.data = {
            "status": "idle", "session": None, "latest": None,
            "history": [], "diagnostic": "",
        }
        coordinator.config = {
            CONF_CHARGING_ENTITY: "binary_sensor.charger",
            CONF_ENERGY_ENTITY: "sensor.energy",
        }
        coordinator.hass = SimpleNamespace(
            states=SimpleNamespace(get=Mock(return_value=SimpleNamespace(state="unavailable")))
        )
        coordinator._unsub = []
        coordinator._async_save = AsyncMock()
        unsubscribe = Mock()

        with patch.object(
            coordinator_module, "async_track_state_change_event",
            return_value=unsubscribe,
        ):
            await coordinator.async_setup()

        self.assertIs(coordinator.data["session"], restored_session)
        self.assertIsNone(restored_session["ended_at"])
        self.assertEqual(coordinator.data["status"], "charging")
        coordinator._async_save.assert_not_awaited()
        self.assertEqual(coordinator._unsub, [unsubscribe])

    async def test_restart_off_marks_restored_active_session_pending_without_losing_history(self):
        import custom_components.ev_charge_tracker.coordinator as coordinator_module
        from custom_components.ev_charge_tracker.const import (
            CONF_CHARGING_ENTITY, CONF_ENERGY_ENTITY, CONF_FINALIZATION,
            FINALIZE_IMMEDIATE,
        )

        restored_session = {
            "started_at": "2026-11-19T08:00:00+00:00",
            "ended_at": None,
            "status": "charging",
            "energy_valid": False,
        }
        coordinator = object.__new__(coordinator_module.EVChargeCoordinator)
        coordinator.store = SimpleNamespace(async_load=AsyncMock(return_value={
            "status": "charging",
            "session": restored_session,
            "latest": None,
            "history": [{"session_id": "older-session"}],
            "diagnostic": "restored",
        }))
        coordinator.data = {
            "status": "idle", "session": None, "latest": None,
            "history": [], "diagnostic": "",
        }
        coordinator.config = {
            CONF_CHARGING_ENTITY: "binary_sensor.charger",
            CONF_ENERGY_ENTITY: "sensor.energy",
            CONF_FINALIZATION: FINALIZE_IMMEDIATE,
        }
        coordinator.hass = SimpleNamespace(
            states=SimpleNamespace(get=Mock(return_value=SimpleNamespace(state="off")))
        )
        coordinator._unsub = []
        coordinator._async_save = AsyncMock()
        coordinator._try_finalize = Mock()
        coordinator._capture_initial_tariff_prices = Mock()
        unsubscribe = Mock()

        with patch.object(
            coordinator_module, "async_track_state_change_event",
            return_value=unsubscribe,
        ):
            await coordinator.async_setup()

        self.assertIsNotNone(restored_session["ended_at"])
        self.assertEqual(restored_session["status"], "pending_finalization")
        self.assertEqual(coordinator.data["status"], "pending_finalization")
        self.assertEqual(coordinator.data["history"][0]["session_id"], "older-session")
        coordinator._try_finalize.assert_called_once()
        coordinator._async_save.assert_awaited_once()

    async def test_delayed_energy_reading_after_stop_is_captured_before_finalization(self):
        from datetime import datetime, timedelta, timezone
        import custom_components.ev_charge_tracker.coordinator as coordinator_module
        from custom_components.ev_charge_tracker.const import (
            CONF_CHARGING_ENTITY, CONF_ENERGY_ENTITY, CONF_FINALIZATION,
            FINALIZE_IMMEDIATE,
        )

        stopped_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        coordinator = object.__new__(coordinator_module.EVChargeCoordinator)
        coordinator.config = {
            CONF_CHARGING_ENTITY: "binary_sensor.charger",
            CONF_ENERGY_ENTITY: "sensor.energy",
            CONF_FINALIZATION: FINALIZE_IMMEDIATE,
        }
        coordinator.data = {
            "status": "pending_finalization",
            "session": {
                "started_at": (stopped_at - timedelta(hours=1)).isoformat(),
                "ended_at": stopped_at.isoformat(),
                "energy_kwh": 0.0,
                "energy_valid": False,
                "last_energy_sample_kwh": 20.0,
                "last_energy_sample_at": (stopped_at - timedelta(minutes=1)).isoformat(),
                "cost_complete": False,
                "tariff_breakdown": {},
            },
            "latest": None,
            "history": [],
            "diagnostic": "",
        }
        energy_state = SimpleNamespace(
            state="22.5",
            attributes={"unit_of_measurement": "kWh"},
            last_updated=datetime.now(timezone.utc),
        )
        charger_state = SimpleNamespace(state="off")
        coordinator.hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda entity_id: (
                charger_state if entity_id == "binary_sensor.charger" else energy_state
            )),
            async_create_task=Mock(),
        )
        coordinator.async_set_updated_data = Mock()
        coordinator._async_save = AsyncMock()
        coordinator._capture_measurements = Mock(
            side_effect=lambda entity_id, value: coordinator.data["session"].update({
                "energy_kwh": 2.5, "energy_valid": True,
                "last_energy_sample_kwh": 22.5,
            })
        )
        coordinator._try_finalize = Mock()

        coordinator._handle_state_change(SimpleNamespace(data={
            "entity_id": "sensor.energy",
            "new_state": energy_state,
        }))

        coordinator._capture_measurements.assert_called_once_with("sensor.energy", "22.5")
        coordinator._try_finalize.assert_called_once()
        coordinator.async_set_updated_data.assert_called_once()
        coordinator.hass.async_create_task.assert_called_once()
        self.assertEqual(coordinator.data["session"]["energy_kwh"], 2.5)
        self.assertTrue(coordinator.data["session"]["energy_valid"])

    async def test_coordinator_shutdown_ignores_already_removed_listener(self):
        from custom_components.ev_charge_tracker.coordinator import EVChargeCoordinator

        coordinator = object.__new__(EVChargeCoordinator)
        already_removed = Mock(side_effect=ValueError("listener already removed"))
        remaining_listener = Mock()
        coordinator._unsub = [already_removed, remaining_listener]
        coordinator._async_save = AsyncMock()

        await coordinator.async_shutdown()

        already_removed.assert_called_once()
        remaining_listener.assert_called_once()
        coordinator._async_save.assert_awaited_once()
        self.assertEqual(coordinator._unsub, [])

    async def test_coordinator_shutdown_unsubscribes_only_once(self):
        from custom_components.ev_charge_tracker.coordinator import EVChargeCoordinator

        coordinator = object.__new__(EVChargeCoordinator)
        unsubscribe = Mock()
        coordinator._unsub = [unsubscribe]
        coordinator._async_save = AsyncMock()

        await coordinator.async_shutdown()
        await coordinator.async_shutdown()

        unsubscribe.assert_called_once()
        self.assertEqual(coordinator._unsub, [])
        self.assertEqual(coordinator._async_save.await_count, 2)


if __name__ == "__main__":
    unittest.main()
