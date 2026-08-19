"""Test complete integration installation in demo mode."""

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
    # Set up homeassistant mocks first
    homeassistant = types.ModuleType("homeassistant")
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)

    exceptions_module = types.ModuleType("homeassistant.exceptions")
    exceptions_module.ConfigEntryNotReady = Exception
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions_module)

    package_name = _install_fake_package(monkeypatch)
    const_name = f"{package_name}.const"
    coordinator_manager_name = f"{package_name}.coordinator_manager"
    coordinator_name = f"{package_name}.coordinator"
    modbus_client_name = f"{package_name}.modbus_client"
    config_entry_utils_name = f"{package_name}.config_entry_utils"
    services_name = f"{package_name}.services"
    module_name = package_name

    _reset_modules(
        module_name,
        const_name,
        coordinator_manager_name,
        coordinator_name,
        modbus_client_name,
        config_entry_utils_name,
        services_name,
    )

    # Import real const module (no HA dependencies)
    const_module = importlib.import_module(const_name)
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock coordinator module
    coordinator_module = types.ModuleType(coordinator_name)

    class FakeDaikinAlthermaNormalCoordinator:
        def __init__(self, hass, host, port, scan_interval, demo_mode):
            self.hass = hass
            self.host = host
            self.port = port
            self.demo_mode = demo_mode
            self.async_add_listener = AsyncMock()
            self.async_config_entry_first_refresh = AsyncMock()

    class FakeDaikinAlthermaSlowCoordinator:
        def __init__(self, hass, host, port, scan_interval, demo_mode):
            self.hass = hass
            self.host = host
            self.port = port
            self.demo_mode = demo_mode
            self.async_add_listener = AsyncMock()
            self.async_config_entry_first_refresh = AsyncMock()

    coordinator_module.DaikinAlthermaNormalCoordinator = FakeDaikinAlthermaNormalCoordinator
    coordinator_module.DaikinAlthermaSlowCoordinator = FakeDaikinAlthermaSlowCoordinator
    monkeypatch.setitem(sys.modules, coordinator_name, coordinator_module)

    # Mock coordinator manager
    coordinator_manager_module = types.ModuleType(coordinator_manager_name)

    class FakeCoordinatorManager:
        last_instance = None

        def __init__(self, hass, host, port, normal_interval, slow_interval, demo_mode):
            self.host = host
            self.port = port
            self.demo_mode = demo_mode
            self.normal = SimpleNamespace()
            self.normal.async_add_listener = AsyncMock()
            self.slow = SimpleNamespace()
            self.slow.async_add_listener = AsyncMock()
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

    # Mock modbus client - in demo mode, connection test should be skipped
    modbus_client_module = types.ModuleType(modbus_client_name)

    class FakeRealModbusTcpClient:
        def __init__(self, host, port, timeout=10):
            self.host = host
            self.port = port
            self._connected = False

        @classmethod
        async def create(cls, host, port, timeout=10):
            return cls(host, port, timeout)

        async def connect(self):
            self._connected = True

        async def disconnect(self):
            self._connected = False

        @property
        def connected(self):
            return self._connected

    FakeRealModbusTcpClient.async_close_cached_client = AsyncMock()
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

    # Mock services module (has HA dependencies)
    services_module = types.ModuleType(services_name)
    services_module.register_services = AsyncMock()
    monkeypatch.setitem(sys.modules, services_name, services_module)

    integration = importlib.import_module(module_name)

    return (
        integration,
        FakeCoordinatorManager,
        FakeUnifiedCoordinator,
        FakeRealModbusTcpClient,
    )


@pytest.mark.asyncio
@pytest.mark.demo_mode
async def test_demo_mode_installation(monkeypatch):
    """Test complete integration installation in demo mode (localhost)."""
    integration, _manager_cls, _unified_cls, _client_cls = _load_integration_module(
        monkeypatch
    )

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(return_value=None),
            async_entries=lambda domain: [],
        ),
    )

    # Demo mode uses localhost as host and demo_mode=True
    entry = SimpleNamespace(
        entry_id="test_entry_demo",
        data={"host": "localhost", "port": 502},
        options={"scan_interval": 15, "slow_scan_interval": 300, "demo_mode": True},
    )

    result = await integration.async_setup_entry(hass, entry)

    # Verify success
    assert result is True

    # Verify coordinators were set up with demo_mode=True
    manager = _manager_cls.last_instance
    unified = _unified_cls.last_instance
    manager.async_setup.assert_awaited_once()
    unified.async_setup.assert_awaited_once()
    assert manager.demo_mode is True
    assert manager.host == "localhost"

    # Verify data stored in hass.data
    assert "ha_daikin_altherma4_modbus" in hass.data
    assert entry.entry_id in hass.data["ha_daikin_altherma4_modbus"]

    stored_data = hass.data["ha_daikin_altherma4_modbus"][entry.entry_id]
    assert stored_data["runtime_data"].coordinator == unified
    assert stored_data["runtime_data"].manager == manager

    # Verify platforms were forwarded
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"]
    )


@pytest.mark.asyncio
@pytest.mark.demo_mode
async def test_demo_mode_skips_connection_test(monkeypatch):
    """Test that demo mode skips the connection test."""
    integration, _manager_cls, _unified_cls, _client_cls = _load_integration_module(
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
        entry_id="test_entry_demo_skip",
        data={"host": "localhost", "port": 502},
        options={"scan_interval": 15, "slow_scan_interval": 300, "demo_mode": True},
    )

    # Track if connection test was attempted
    connection_attempts = []
    original_create = _client_cls.create

    async def tracked_create(host, port, timeout=10):
        connection_attempts.append((host, port))
        return await original_create(host, port, timeout)

    _client_cls.create = tracked_create

    result = await integration.async_setup_entry(hass, entry)

    # Verify success
    assert result is True

    # In demo mode, connection test should be skipped
    # The RealModbusTcpClient.create should NOT be called during setup
    assert len(connection_attempts) == 0
