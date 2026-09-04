"""Tests for repair_flow.py."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _stub_config_flow():
    """Stub config_flow module imports needed by repair_flow."""
    import sys
    from types import ModuleType

    # Ensure config_entry_utils is stubbed
    mod_name = (
        "custom_components.ha_daikin_altherma4_modbus.integration.config_entry_utils"
    )
    utils_mod = ModuleType(mod_name)
    utils_mod.entry_data_value = lambda entry, key, default: default
    utils_mod.entry_value = lambda entry, key: (
        entry.data.get(key) if hasattr(entry, "data") else None
    )
    sys.modules[mod_name] = utils_mod

    # Always force-set config_flow stub to ensure _build_fix_schema is available
    cf_mod = ModuleType(
        "custom_components.ha_daikin_altherma4_modbus.integration.config_flow"
    )
    cf_mod._build_fix_schema = lambda host="", port=502: {
        "host": host,
        "port": port,
    }
    cf_mod._is_valid_host = lambda host: bool(host)
    cf_mod._test_connection = AsyncMock(return_value=(True, None))
    cf_mod._connection_unique_id = lambda host, port: f"{host}:{port}"

    class _StubConfigFlow:
        def async_abort(self, *, reason):
            return {"reason": reason}

        def async_show_form(self, **kwargs):
            return kwargs

    cf_mod.ConfigFlow = _StubConfigFlow
    sys.modules[
        "custom_components.ha_daikin_altherma4_modbus.integration.config_flow"
    ] = cf_mod

    # Also force-set repair_flow to ensure it picks up the stubbed config_flow
    if (
        "custom_components.ha_daikin_altherma4_modbus.integration.repair_flow"
        in sys.modules
    ):
        del sys.modules[
            "custom_components.ha_daikin_altherma4_modbus.integration.repair_flow"
        ]


@pytest.mark.asyncio
async def test_repair_flow_init_starts_fix_connection():
    """Test that async_step_init delegates to fix_connection."""
    from custom_components.ha_daikin_altherma4_modbus.integration.repair_flow import (
        ConnectionLostFixFlow,
    )

    flow = ConnectionLostFixFlow()
    flow.context = {"entry_id": "test_entry"}
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(
                data={"host": "192.168.1.100", "port": 502},
                options={},
            )
        )
    )

    result = await flow.async_step_init()
    assert result["step_id"] == "fix_connection"


@pytest.mark.asyncio
async def test_repair_flow_aborts_on_missing_entry():
    """Test that fix_connection aborts when entry is not found."""
    from custom_components.ha_daikin_altherma4_modbus.integration.repair_flow import (
        ConnectionLostFixFlow,
    )

    flow = ConnectionLostFixFlow()
    flow.context = {"entry_id": "nonexistent"}
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: None,
        )
    )

    result = await flow.async_step_fix_connection()
    assert result["reason"] == "entry_not_found"


@pytest.mark.asyncio
async def test_repair_flow_updates_entry_on_valid_input():
    """Test that fix_connection updates entry and reloads."""
    from custom_components.ha_daikin_altherma4_modbus.integration.repair_flow import (
        ConnectionLostFixFlow,
    )

    mock_entry = SimpleNamespace(
        data={"host": "192.168.1.100", "port": 502},
        options={},
        entry_id="test_entry",
    )
    reload_called = False

    async def async_reload(entry_id):
        nonlocal reload_called
        reload_called = True

    flow = ConnectionLostFixFlow()
    flow.context = {"entry_id": "test_entry"}
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: mock_entry,
            async_update_entry=lambda entry, **kw: None,
            async_reload=async_reload,
        )
    )

    result = await flow.async_step_fix_connection(
        {
            "host": "192.168.1.200",
            "port": 502,
        }
    )
    assert result["reason"] == "fix_successful"
    assert reload_called
