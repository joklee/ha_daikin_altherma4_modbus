import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def _reset_modules(*names: str) -> None:
    """Reset modules for clean testing."""
    for name in names:
        sys.modules.pop(name, None)


def _install_fake_package(monkeypatch) -> str:
    """Install fake package for testing."""
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    package_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _load_integration_module(monkeypatch):
    """Load integration module with mocked dependencies."""
    package_name = _install_fake_package(monkeypatch)
    const_name = f"{package_name}.const"
    coordinator_manager_name = f"{package_name}.coordinator_manager"
    modbus_client_name = f"{package_name}.modbus_client"
    config_entry_utils_name = f"{package_name}.config_entry_utils"
    module_name = package_name

    _reset_modules(
        module_name,
        const_name,
        coordinator_manager_name,
        modbus_client_name,
        config_entry_utils_name,
    )

    # Mock const module
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SLOW_SCAN_INTERVAL = 600
    const_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock coordinator manager
    coordinator_manager_module = types.ModuleType(coordinator_manager_name)

    class FakeCoordinatorManager:
        last_instance = None

        def __init__(self, hass, host, port, normal_interval, slow_interval, demo_mode):
            self.host = host
            self.port = port
            self.normal = SimpleNamespace()
            self.slow = SimpleNamespace()
            self.async_setup = AsyncMock()
            self.async_shutdown = AsyncMock()
            FakeCoordinatorManager.last_instance = self

        def get_coordinator(self, coordinator_type):
            return self.normal if coordinator_type == "normal" else self.slow

    class FakeUnifiedCoordinator:
        last_instance = None

        def __init__(self, hass, manager, normal_coordinator, slow_coordinator):
            self.data = {"test_data": "value"}
            self.async_setup = AsyncMock()
            self.async_shutdown = AsyncMock()
            FakeUnifiedCoordinator.last_instance = self

    coordinator_manager_module.CoordinatorManager = FakeCoordinatorManager
    coordinator_manager_module.UnifiedCoordinator = FakeUnifiedCoordinator
    monkeypatch.setitem(
        sys.modules, coordinator_manager_name, coordinator_manager_module
    )

    # Mock modbus client
    modbus_client_module = types.ModuleType(modbus_client_name)

    class FakeRealModbusTcpClient:
        async_close_cached_client = AsyncMock()

    modbus_client_module.RealModbusTcpClient = FakeRealModbusTcpClient
    monkeypatch.setitem(sys.modules, modbus_client_name, modbus_client_module)

    # Mock config entry utils
    config_entry_utils_module = types.ModuleType(config_entry_utils_name)

    def entry_value(entry, key, default=None):
        return entry.options.get(key, default)

    def entry_data_value(entry, key, default=None):
        return entry.data.get(key, default)

    config_entry_utils_module.entry_value = entry_value
    config_entry_utils_module.entry_data_value = entry_data_value
    monkeypatch.setitem(sys.modules, config_entry_utils_name, config_entry_utils_module)

    integration = importlib.import_module(module_name)

    return (
        integration,
        FakeCoordinatorManager,
        FakeUnifiedCoordinator,
        FakeRealModbusTcpClient,
    )


@pytest.mark.asyncio
async def test_async_setup_entry_success(monkeypatch):
    """Test successful async_setup_entry execution."""
    integration, manager_cls, unified_cls, client_cls = _load_integration_module(
        monkeypatch
    )

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(return_value=None),
            async_entries=lambda domain: [],
        ),
    )

    entry = SimpleNamespace(
        entry_id="test_entry_1",
        data={"host": "192.168.1.100", "port": 502},
        options={"scan_interval": 15, "slow_scan_interval": 300, "demo_mode": False},
    )

    result = await integration.async_setup_entry(hass, entry)

    # Verify success
    assert result is True

    # Verify coordinators were set up
    manager = manager_cls.last_instance
    unified = unified_cls.last_instance
    manager.async_setup.assert_awaited_once()
    unified.async_setup.assert_awaited_once()

    # Verify data stored in hass.data
    assert "ha_daikin_altherma4_modbus" in hass.data
    assert entry.entry_id in hass.data["ha_daikin_altherma4_modbus"]

    stored_data = hass.data["ha_daikin_altherma4_modbus"][entry.entry_id]
    assert stored_data["runtime_data"].coordinator == unified
    assert stored_data["runtime_data"].manager == manager
    assert stored_data["runtime_data"].normal_coordinator == manager.normal
    assert stored_data["runtime_data"].slow_coordinator == manager.slow

    # Verify platforms were forwarded
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"]
    )


@pytest.mark.asyncio
async def test_async_unload_entry_success(monkeypatch):
    """Test successful async_unload_entry execution."""
    integration, manager_cls, unified_cls, client_cls = _load_integration_module(
        monkeypatch
    )

    # Set up initial state with runtime data
    from types import SimpleNamespace

    class MockRuntimeData:
        def __init__(self, coordinator, manager):
            self.coordinator = coordinator
            self.manager = manager
            self.normal_coordinator = SimpleNamespace()
            self.slow_coordinator = SimpleNamespace()

    manager = SimpleNamespace(
        host="192.168.1.100", port=502, async_shutdown=AsyncMock()
    )
    unified_coordinator = SimpleNamespace(async_shutdown=AsyncMock())
    runtime_data = MockRuntimeData(unified_coordinator, manager)

    hass = SimpleNamespace()
    hass.data = {
        "ha_daikin_altherma4_modbus": {
            "test_entry_1": {
                "runtime_data": runtime_data,
            }
        }
    }
    hass.config_entries = SimpleNamespace(
        async_unload_platforms=AsyncMock(return_value=True),
        async_entries=lambda domain: [],
    )

    entry = SimpleNamespace(
        entry_id="test_entry_1",
        data={"host": "192.168.1.100", "port": 502},
        runtime_data=runtime_data,
    )

    result = await integration.async_unload_entry(hass, entry)

    # Verify success
    assert result is True

    # Verify platforms were unloaded
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"]
    )

    # Verify coordinators were shut down
    unified_coordinator.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)

    # Verify client was closed (no shared endpoint)
    client_cls.async_close_cached_client.assert_awaited_once_with("192.168.1.100", 502)

    # Verify entry data was removed
    assert "test_entry_1" not in hass.data.get("ha_daikin_altherma4_modbus", {})
    assert "ha_daikin_altherma4_modbus" not in hass.data  # Should be empty now


@pytest.mark.asyncio
async def test_async_setup_entry_unified_coordinator_failure(monkeypatch):
    """Test error handling when unified coordinator setup fails."""
    integration, manager_cls, unified_cls, client_cls = _load_integration_module(
        monkeypatch
    )

    # Mock unified coordinator setup to fail
    original_init = unified_cls.__init__

    def failing_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.async_setup = AsyncMock(
            side_effect=RuntimeError("Unified coordinator setup failed")
        )

    unified_cls.__init__ = failing_init

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(), async_entries=lambda domain: []
        ),
    )

    entry = SimpleNamespace(
        entry_id="test_entry_1",
        data={"host": "192.168.1.100", "port": 502},
        options={"scan_interval": 15, "slow_scan_interval": 300, "demo_mode": False},
    )

    result = await integration.async_setup_entry(hass, entry)

    # Verify failure
    assert result is False

    # Verify rollback occurred
    manager = manager_cls.last_instance
    unified = unified_cls.last_instance
    unified.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)
    client_cls.async_close_cached_client.assert_awaited_once_with("192.168.1.100", 502)

    # Verify no data stored
    assert "ha_daikin_altherma4_modbus" not in hass.data

    # Verify platforms were not forwarded
    hass.config_entries.async_forward_entry_setups.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_setup_entry_platform_forward_failure(monkeypatch):
    """Test error handling when platform forwarding fails."""
    integration, manager_cls, unified_cls, client_cls = _load_integration_module(
        monkeypatch
    )

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(
                side_effect=RuntimeError("Platform forward failed")
            ),
            async_entries=lambda domain: [],
        ),
    )

    entry = SimpleNamespace(
        entry_id="test_entry_1",
        data={"host": "192.168.1.100", "port": 502},
        options={"scan_interval": 15, "slow_scan_interval": 300, "demo_mode": False},
    )

    result = await integration.async_setup_entry(hass, entry)

    # Verify failure
    assert result is False

    # Verify rollback occurred
    manager = manager_cls.last_instance
    unified = unified_cls.last_instance
    unified.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)
    client_cls.async_close_cached_client.assert_awaited_once_with("192.168.1.100", 502)

    # Verify data was cleaned up
    assert "ha_daikin_altherma4_modbus" not in hass.data


@pytest.mark.asyncio
async def test_async_setup_entry_manager_setup_failure(monkeypatch):
    """Test error handling when manager setup fails."""
    integration, manager_cls, unified_cls, client_cls = _load_integration_module(
        monkeypatch
    )

    # Mock manager setup to fail
    original_init = manager_cls.__init__

    def failing_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.async_setup = AsyncMock(side_effect=RuntimeError("Manager setup failed"))

    manager_cls.__init__ = failing_init

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(), async_entries=lambda domain: []
        ),
    )

    entry = SimpleNamespace(
        entry_id="test_entry_1",
        data={"host": "192.168.1.100", "port": 502},
        options={"scan_interval": 15, "slow_scan_interval": 300, "demo_mode": False},
    )

    result = await integration.async_setup_entry(hass, entry)

    # Verify failure
    assert result is False

    # Verify rollback occurred
    manager = manager_cls.last_instance
    unified = unified_cls.last_instance
    unified.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)
    client_cls.async_close_cached_client.assert_awaited_once_with("192.168.1.100", 502)

    # Verify no data stored
    assert "ha_daikin_altherma4_modbus" not in hass.data
