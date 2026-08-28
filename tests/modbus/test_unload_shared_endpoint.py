import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

# Load real const first at module import time to avoid executing __init__.py during reload purge
import custom_components.ha_daikin_altherma4_modbus.core.const as real_const


def _load_integration_module(monkeypatch, close_cached_client_mock: AsyncMock):
    """Load integration __init__ with lightweight dependency stubs."""
    # Set up homeassistant mocks first
    homeassistant = types.ModuleType("homeassistant")
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)

    exceptions_module = types.ModuleType("homeassistant.exceptions")
    exceptions_module.ConfigEntryNotReady = Exception
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions_module)

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )
    update_coordinator_module.DataUpdateCoordinator = object
    update_coordinator_module.UpdateFailed = Exception
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator_module,
    )

    package_name = "custom_components.ha_daikin_altherma4_modbus"
    const_name = f"{package_name}.core.const"
    coordinator_manager_name = f"{package_name}.coordinator_manager"
    modbus_client_name = f"{package_name}.modbus.modbus_client"
    config_entry_utils_name = f"{package_name}.config_entry_utils"

    # Pop all submodules of the package to guarantee a 100% clean reload
    for key in list(sys.modules.keys()):
        if key == package_name or key.startswith(package_name + "."):
            sys.modules.pop(key, None)

    config_entry_utils_module = types.ModuleType(config_entry_utils_name)
    config_entry_utils_module.entry_value = lambda entry, key, default=None: (
        entry.options.get(key, default)
    )
    config_entry_utils_module.entry_data_value = lambda entry, key, default=None: (
        entry.data.get(key, default)
    )
    monkeypatch.setitem(sys.modules, config_entry_utils_name, config_entry_utils_module)

    const_module = types.ModuleType(const_name)
    for key, val in real_const.__dict__.items():
        setattr(const_module, key, val)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SLOW_SCAN_INTERVAL = 600
    const_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, const_name, const_module)

    coordinator_manager_module = types.ModuleType(coordinator_manager_name)
    coordinator_manager_module.CoordinatorManager = object
    coordinator_manager_module.UnifiedCoordinator = object
    monkeypatch.setitem(
        sys.modules, coordinator_manager_name, coordinator_manager_module
    )

    modbus_client_module = types.ModuleType(modbus_client_name)

    class FakeRealModbusTcpClient:
        async_close_cached_client = close_cached_client_mock

    modbus_client_module.RealModbusTcpClient = FakeRealModbusTcpClient
    monkeypatch.setitem(sys.modules, modbus_client_name, modbus_client_module)

    return importlib.import_module(package_name)


@pytest.mark.asyncio
async def test_unload_keeps_shared_endpoint_client(monkeypatch):
    close_cached_client_mock = AsyncMock()
    integration = _load_integration_module(monkeypatch, close_cached_client_mock)

    domain = "ha_daikin_altherma4_modbus"
    shared_host = "192.168.1.10"
    shared_port = 502

    manager_1 = SimpleNamespace(
        host=shared_host, port=shared_port, async_shutdown=AsyncMock()
    )
    manager_2 = SimpleNamespace(
        host=shared_host, port=shared_port, async_shutdown=AsyncMock()
    )
    unified_coordinator_1 = SimpleNamespace(async_shutdown=AsyncMock())

    class MockRuntimeData:
        def __init__(self, coordinator, manager):
            self.coordinator = coordinator
            self.manager = manager

    runtime_data_1 = MockRuntimeData(unified_coordinator_1, manager_1)
    runtime_data_2 = MockRuntimeData(
        SimpleNamespace(async_shutdown=AsyncMock()), manager_2
    )

    # Create mock entries for the shared endpoint test
    entry_1 = SimpleNamespace(
        entry_id="entry_1",
        data={"host": shared_host, "port": shared_port},
        runtime_data=runtime_data_1,
    )
    entry_2 = SimpleNamespace(
        entry_id="entry_2",
        data={"host": shared_host, "port": shared_port},
        runtime_data=runtime_data_2,
    )

    hass = SimpleNamespace()
    hass.data = {
        domain: {
            "entry_1": {
                "runtime_data": runtime_data_1,
            },
            "entry_2": {
                "runtime_data": runtime_data_2,
            },
        }
    }
    hass.config_entries = SimpleNamespace(
        async_unload_platforms=AsyncMock(return_value=True),
        async_entries=lambda domain: [entry_1, entry_2],
    )

    entry = entry_1

    unload_ok = await integration.async_unload_entry(hass, entry)

    assert unload_ok is True
    unified_coordinator_1.async_shutdown.assert_awaited_once()
    manager_1.async_shutdown.assert_awaited_once_with(disconnect_clients=False)
    close_cached_client_mock.assert_not_awaited()
    assert "entry_1" not in hass.data[domain]
    assert "entry_2" in hass.data[domain]


@pytest.mark.asyncio
async def test_unload_closes_client_when_endpoint_not_shared(monkeypatch):
    close_cached_client_mock = AsyncMock()
    integration = _load_integration_module(monkeypatch, close_cached_client_mock)

    domain = "ha_daikin_altherma4_modbus"
    host = "192.168.1.20"
    port = 502

    manager = SimpleNamespace(host=host, port=port, async_shutdown=AsyncMock())
    unified_coordinator = SimpleNamespace(async_shutdown=AsyncMock())

    class MockRuntimeData:
        def __init__(self, coordinator, manager):
            self.coordinator = coordinator
            self.manager = manager

    runtime_data = MockRuntimeData(unified_coordinator, manager)

    hass = SimpleNamespace()
    hass.data = {
        domain: {
            "entry_1": {
                "runtime_data": runtime_data,
            }
        }
    }
    hass.config_entries = SimpleNamespace(
        async_unload_platforms=AsyncMock(return_value=True),
        async_entries=lambda domain: [],
    )

    entry = SimpleNamespace(
        entry_id="entry_1", data={"host": host, "port": port}, runtime_data=runtime_data
    )

    unload_ok = await integration.async_unload_entry(hass, entry)

    assert unload_ok is True
    unified_coordinator.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)
    close_cached_client_mock.assert_awaited_once_with(host, port)
    assert domain not in hass.data
