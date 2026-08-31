"""Real-HA setup failure and connection error integration tests under tests/ha/."""

from unittest import mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.modbus.modbus_client import (
    RealModbusTcpClient,
)

HOST = "192.0.2.50"
PORT = 502


@pytest.mark.real_ha
async def test_setup_entry_connection_failure_raises_config_entry_not_ready(
    hass, enable_custom_integrations
):
    """When setup fails to connect, ConfigEntryNotReady is raised and state becomes SETUP_RETRY."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Daikin Altherma 4 ({HOST})",
        unique_id=f"{HOST}:{PORT}",
        data={CONF_HOST: HOST, CONF_PORT: PORT},
    )
    entry.add_to_hass(hass)

    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        side_effect=Exception("Connection refused"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is False
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
