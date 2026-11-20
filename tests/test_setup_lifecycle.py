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

        self.coordinator.async_shutdown.assert_awaited_once()
        self.assertNotIn(self.entry.entry_id, self.hass.data[DOMAIN])

    async def test_successful_setup_keeps_coordinator_registered(self):
        with patch.object(integration, "EVChargeCoordinator", return_value=self.coordinator):
            result = await integration.async_setup_entry(self.hass, self.entry)

        self.assertTrue(result)
        self.assertIs(self.hass.data[DOMAIN][self.entry.entry_id], self.coordinator)
        self.coordinator.async_shutdown.assert_not_awaited()
        self.entry.async_on_unload.assert_called_once()


if __name__ == "__main__":
    unittest.main()
