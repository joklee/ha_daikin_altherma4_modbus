"""Setup/unload/coordinator edge paths with the real integration module.

All tests stay offline: demo mode uses the mock client, and non-demo tests
stub the ``config_flow._test_connection`` seam. Covers migration,
endpoint sharing, probe failures, setup rollback, unload failures and
coordinator ``UpdateFailed`` handling with repair issues.
"""

from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.issue_registry import async_get as async_get_issue_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus import (
    _has_other_entry_for_endpoint,
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ha_daikin_altherma4_modbus.core.const import (
    CONF_UNIT_ID,
    DOMAIN,
)
from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusConnectionException,
    ModbusInvalidAddressException,
)
from custom_components.ha_daikin_altherma4_modbus.integration import (
    config_flow as config_flow_module,
)


def _demo_entry(**overrides):
    data = {CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1}
    options = {"scan_interval": 5, "slow_scan_interval": 30, "demo_mode": True}
    data.update(overrides.pop("data", {}))
    options.update(overrides.pop("options", {}))
    return MockConfigEntry(
        domain=DOMAIN,
        title="Daikin Altherma 4 (192.0.2.10)",
        unique_id="192.0.2.10:502",
        data=data,
        options=options,
        version=2,
        **overrides,
    )


async def test_migrate_v1_adds_default_unit_id():
    """Version-1 entries gain the default unit id."""
    hass = SimpleNamespace(config_entries=SimpleNamespace())
    updated = {}

    def fake_update(entry, *, data, version):
        updated["data"] = data
        updated["version"] = version

    hass.config_entries.async_update_entry = fake_update
    entry = SimpleNamespace(version=1, data={CONF_HOST: "h", CONF_PORT: 502})

    assert await async_migrate_entry(hass, entry) is True
    assert updated["data"][CONF_UNIT_ID] == 1
    assert updated["data"][CONF_HOST] == "h"
    assert updated["version"] == 2


async def test_migrate_v2_is_noop():
    """Already-migrated entries are left untouched."""
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=MagicMock())
    )
    entry = SimpleNamespace(
        version=2, data={CONF_HOST: "h", CONF_PORT: 502, CONF_UNIT_ID: 3}
    )

    assert await async_migrate_entry(hass, entry) is True
    hass.config_entries.async_update_entry.assert_not_called()


def test_has_other_entry_for_endpoint():
    """Endpoint sharing is detected across entries, excluding self."""
    me = SimpleNamespace(
        entry_id="me",
        runtime_data=SimpleNamespace(
            manager=SimpleNamespace(host="192.0.2.10", port=502)
        ),
    )
    other = SimpleNamespace(
        entry_id="other",
        runtime_data=SimpleNamespace(
            manager=SimpleNamespace(host="192.0.2.99", port=502)
        ),
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: [me, other])
    )
    assert _has_other_entry_for_endpoint(hass, "me", "192.0.2.99", 502) is True
    assert _has_other_entry_for_endpoint(hass, "me", "192.0.2.10", 502) is False
    assert _has_other_entry_for_endpoint(hass, "other", "192.0.2.99", 502) is False

    hass.config_entries.async_entries = lambda domain: [
        SimpleNamespace(entry_id="bare")
    ]
    assert _has_other_entry_for_endpoint(hass, "me", "192.0.2.10", 502) is False


async def test_demo_setup_and_unload_roundtrip(hass, enable_custom_integrations):
    """Full demo setup forwards platforms; unload tears everything down."""
    entry = _demo_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None

    assert await hass.config_entries.async_unload(entry.entry_id) is True
    await hass.async_block_till_done()


async def test_setup_probe_exception_becomes_not_ready(
    hass, enable_custom_integrations
):
    """A crashing probe surfaces as ConfigEntryNotReady with a repair issue."""
    entry = _demo_entry(options={"demo_mode": False})
    entry.add_to_hass(hass)

    with (
        mock.patch.object(
            config_flow_module,
            "_test_connection",
            new=mock.AsyncMock(side_effect=RuntimeError("probe exploded")),
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)

    registry = async_get_issue_registry(hass)
    assert (DOMAIN, f"connection_lost_{entry.entry_id}") in registry.issues


async def test_setup_rollback_on_forward_failure(hass, enable_custom_integrations):
    """A late setup failure rolls back runtime data and raises."""
    entry = _demo_entry()
    entry.add_to_hass(hass)

    with (
        mock.patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(side_effect=RuntimeError("platform boom")),
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)

    assert DOMAIN not in hass.data


async def test_unload_without_runtime_data_returns_false(
    hass, enable_custom_integrations
):
    """Unload without prior setup fails gracefully."""
    entry = _demo_entry()
    entry.add_to_hass(hass)
    assert await async_unload_entry(hass, entry) is False


async def test_unload_swallows_manager_shutdown_error(hass, enable_custom_integrations):
    """A failing manager shutdown does not fail the unload."""
    entry = _demo_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()

    with mock.patch.object(
        entry.runtime_data.manager,
        "async_shutdown",
        new=AsyncMock(side_effect=RuntimeError("shutdown boom")),
    ):
        assert await hass.config_entries.async_unload(entry.entry_id) is True
    await hass.async_block_till_done()


async def test_coordinator_failure_creates_repair_issue(
    hass, enable_custom_integrations, caplog
):
    """Coordinator UpdateFailed paths create a repair issue via entry lookup."""
    entry = _demo_entry()
    entry.add_to_hass(hass)
    # A second entry without runtime data exercises the lookup skip branch.
    MockConfigEntry(domain=DOMAIN, unique_id="other:1", data={}).add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()

    coordinator = entry.runtime_data.normal_coordinator
    coordinator.data_manager = SimpleNamespace(
        fetch_input_registers_data=AsyncMock(
            side_effect=ModbusConnectionException("dead gateway")
        ),
        fetch_discrete_inputs_data=AsyncMock(return_value={}),
    )
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    registry = async_get_issue_registry(hass)
    assert (DOMAIN, f"connection_lost_{entry.entry_id}") in registry.issues

    # Recovery clears the issue and resets the flags.
    coordinator.data_manager = SimpleNamespace(
        fetch_input_registers_data=AsyncMock(return_value={"input_40": {}}),
        fetch_discrete_inputs_data=AsyncMock(return_value={}),
    )
    await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    assert (DOMAIN, f"connection_lost_{entry.entry_id}") not in registry.issues


async def test_slow_coordinator_failure_paths(hass, enable_custom_integrations):
    """Slow coordinator maps transport and address errors to UpdateFailed."""
    entry = _demo_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()

    coordinator = entry.runtime_data.slow_coordinator
    coordinator.data_manager = SimpleNamespace(
        refresh_coils=AsyncMock(side_effect=ModbusConnectionException("dead gateway")),
        refresh_holding_registers=AsyncMock(return_value={}),
    )
    await coordinator.async_refresh()
    assert coordinator.last_update_success is False

    coordinator.data_manager = SimpleNamespace(
        refresh_coils=AsyncMock(return_value={}),
        refresh_holding_registers=AsyncMock(
            side_effect=ModbusInvalidAddressException("no block")
        ),
    )
    await coordinator.async_refresh()
    assert coordinator.last_update_success is False
