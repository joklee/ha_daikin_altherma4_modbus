"""Real-HA setup failure and connection error integration tests under tests/ha/."""

from unittest import mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.integration import (
    config_flow as config_flow_module,
)
from custom_components.ha_daikin_altherma4_modbus.integration.repair import (
    unsupported_temperature_unit_issue_id,
)

HOST = "192.0.2.50"
PORT = 502


def _demo_entry() -> MockConfigEntry:
    """Return a demo-mode entry so no real Modbus socket is opened."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Daikin Altherma 4 ({HOST})",
        unique_id=f"{HOST}:{PORT}:1",
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        options={"scan_interval": 5, "slow_scan_interval": 30, "demo_mode": True},
    )


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
        config_flow_module,
        "_test_connection",
        new=mock.AsyncMock(return_value=(False, "cannot_connect")),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is False
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.real_ha
async def test_setup_entry_under_fahrenheit_is_blocked(
    hass, enable_custom_integrations
):
    """Fahrenheit blocks setup with SETUP_ERROR, a repair issue and no entities."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    entry = _demo_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is False
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR

    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, unsupported_temperature_unit_issue_id(entry)
    )
    assert issue is not None
    assert issue.severity is IssueSeverity.ERROR
    assert issue.translation_key == "unsupported_temperature_unit"
    assert issue.translation_placeholders["temperature_unit"] == "°F"
    assert issue.config_entry_id == entry.entry_id

    # The guard runs before any platform setup, so no entity is registered.
    registry = er.async_get(hass)
    assert [
        item for item in registry.entities.values() if item.platform == DOMAIN
    ] == []


@pytest.mark.real_ha
async def test_metric_setup_clears_stale_fahrenheit_issue(
    hass, enable_custom_integrations
):
    """Switching back to metric recovers the entry and deletes the repair issue."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    entry = _demo_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is False
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, unsupported_temperature_unit_issue_id(entry)
        )
        is not None
    )

    hass.config.units = METRIC_SYSTEM
    assert await hass.config_entries.async_reload(entry.entry_id) is True
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, unsupported_temperature_unit_issue_id(entry)
        )
        is None
    )
