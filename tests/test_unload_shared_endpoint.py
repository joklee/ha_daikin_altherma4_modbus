import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def _load_integration_module(monkeypatch, close_cached_client_mock: AsyncMock):
    """Load integration __init__ with lightweight dependency stubs."""
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    const_name = f"{package_name}.const"
    coordinator_manager_name = f"{package_name}.coordinator_manager"
    modbus_client_name = f"{package_name}.modbus_client"

    for name in (
        package_name,
        const_name,
        coordinator_manager_name,
        modbus_client_name,
    ):
        sys.modules.pop(name, None)

    const_module = types.ModuleType(const_name)
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

    hass = SimpleNamespace()
    hass.data = {
        domain: {
            "entry_1": {
                "manager": manager_1,
                "coordinator": unified_coordinator_1,
            },
            "entry_2": {
                "manager": manager_2,
                "coordinator": SimpleNamespace(async_shutdown=AsyncMock()),
            },
        }
    }
    hass.config_entries = SimpleNamespace(
        async_unload_platforms=AsyncMock(return_value=True)
    )

    entry = SimpleNamespace(
        entry_id="entry_1",
        data={"host": shared_host, "port": shared_port},
    )

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

    hass = SimpleNamespace()
    hass.data = {
        domain: {
            "entry_1": {
                "manager": manager,
                "coordinator": unified_coordinator,
            }
        }
    }
    hass.config_entries = SimpleNamespace(
        async_unload_platforms=AsyncMock(return_value=True)
    )

    entry = SimpleNamespace(
        entry_id="entry_1",
        data={"host": host, "port": port},
    )

    unload_ok = await integration.async_unload_entry(hass, entry)

    assert unload_ok is True
    unified_coordinator.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)
    close_cached_client_mock.assert_awaited_once_with(host, port)
    assert domain not in hass.data
