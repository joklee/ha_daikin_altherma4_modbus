"""Integration lifecycle tests for ha_daikin_altherma4_modbus integration."""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _restore_module_state():
    """Snapshot & restore ``sys.modules`` for stubbed namespaces.

    The loaders below re-import the integration while stub modules are
    installed; without a restore, the re-import caches poisoned modules in
    ``sys.modules`` and breaks later real-HA tests in the same process.
    (Same pattern as tests/modbus/test_unload_shared_endpoint.py.)
    """
    prefixes = ("homeassistant", "custom_components")

    def _is_tracked(key: str) -> bool:
        return key.startswith(prefixes)

    snapshot = {key: module for key, module in sys.modules.items() if _is_tracked(key)}

    yield

    for key in [key for key in list(sys.modules) if _is_tracked(key)]:
        sys.modules.pop(key, None)
    sys.modules.update(snapshot)


def _reset_modules(*names: str) -> None:
    """Reset modules for clean testing."""
    for name in names:
        sys.modules.pop(name, None)


def _install_fake_package(monkeypatch) -> str:
    """Install fake package for testing."""
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    package_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _load_integration_module(monkeypatch):
    """Load integration module with mocked dependencies.

    Only integration-internal modules (const, coordinator_manager,
    modbus_client, config_entry_utils, repair, runtime_data, services) are
    replaced; Home Assistant is used from the real installed distribution.
    """
    package_name = _install_fake_package(monkeypatch)
    const_name = f"{package_name}.const"
    coordinator_manager_name = f"{package_name}.integration.coordinator_manager"
    modbus_client_name = f"{package_name}.modbus.modbus_client"
    connection_manager_name = f"{package_name}.modbus.connection_manager"
    config_entry_utils_name = f"{package_name}.integration.config_entry_utils"
    config_flow_name = f"{package_name}.integration.config_flow"
    repair_name = f"{package_name}.integration.repair"
    runtime_data_name = f"{package_name}.runtime_data"
    services_name = f"{package_name}.integration.services"
    module_name = package_name

    _reset_modules(
        module_name,
        const_name,
        coordinator_manager_name,
        modbus_client_name,
        connection_manager_name,
        config_entry_utils_name,
        config_flow_name,
        repair_name,
        runtime_data_name,
        services_name,
    )

    # Mock const module
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.NORMAL_SCAN_INTERVAL = 10
    const_module.SLOW_SCAN_INTERVAL = 600
    const_module.DEFAULT_PORT = 502
    const_module.CONF_HOST = "host"
    const_module.CONF_PORT = "port"
    const_module.CONF_SCAN_INTERVAL = "scan_interval"
    const_module.CONF_SLOW_SCAN_INTERVAL = "slow_scan_interval"
    const_module.CONF_ELECTRIC_POWER_SENSOR = "electric_power_sensor"
    const_module.CONF_DEMO_MODE = "demo_mode"
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock config_entry_utils module
    config_entry_utils_module = types.ModuleType(config_entry_utils_name)

    def entry_value(entry, key, default=None):
        """Read config value from options first, then fallback to data."""
        options = getattr(entry, "options", {}) or {}
        data = getattr(entry, "data", {}) or {}
        return options.get(key, data.get(key, default))

    def entry_data_value(entry, key, default=None):
        """Read config value from entry data only."""
        data = getattr(entry, "data", {}) or {}
        return data.get(key, default)

    config_entry_utils_module.entry_value = entry_value
    config_entry_utils_module.entry_data_value = entry_data_value
    config_entry_utils_module.get_host = lambda entry: entry.data.get(
        "host", "192.168.1.100"
    )
    config_entry_utils_module.get_port = lambda entry: entry.data.get("port", 502)
    config_entry_utils_module.get_scan_interval = lambda entry: entry.options.get(
        "scan_interval", 10
    )
    config_entry_utils_module.get_slow_scan_interval = lambda entry: entry.options.get(
        "slow_scan_interval", 600
    )
    config_entry_utils_module.get_electric_power_sensor = lambda entry: (
        entry.options.get("electric_power_sensor", "")
    )
    config_entry_utils_module.get_demo_mode = lambda entry: entry.options.get(
        "demo_mode", False
    )
    monkeypatch.setitem(sys.modules, config_entry_utils_name, config_entry_utils_module)

    # Mock modbus_client module
    modbus_client_module = types.ModuleType(modbus_client_name)

    class MockModbusTcpClient:
        def __init__(self, host, port=502, timeout=10):
            self.host = host
            self.port = port
            self.timeout = timeout
            self.connected = False

        async def connect(self):
            self.connected = True
            return True

        async def disconnect(self):
            self.connected = False

        async def read_input_registers(self, address, count):
            return None

        async def read_holding_registers(self, address, count):
            return None

        async def read_discrete_inputs(self, address, count):
            return None

        async def read_coils(self, address, count):
            return None

        async def write_single_register(self, address, value):
            return None

        async def write_single_coil(self, address, value):
            return None

    modbus_client_module.MockModbusTcpClient = MockModbusTcpClient
    modbus_client_module.RealModbusTcpClient = MockModbusTcpClient
    monkeypatch.setitem(sys.modules, modbus_client_name, modbus_client_module)

    # Mock connection_manager module
    connection_manager_name = f"{package_name}.modbus.connection_manager"
    connection_manager_module = types.ModuleType(connection_manager_name)

    async def mock_async_test_connection_with_temporary_unit(hass, host, port, unit_id):
        """Mock connection test that always succeeds."""
        return True, None

    async def mock_async_get_ha_unit(hass, entry, host, port, unit_id):
        """Mock HA unit getter that returns a mock client."""
        return MockModbusTcpClient(host, port)

    async def mock_connect_modbus_client(
        client, host, port, connection_type="connection"
    ):
        """Mock connect helper."""
        client.connected = True

    async def mock_ensure_modbus_connection(client, host, port, demo_mode=False):
        """Mock ensure helper returning the existing client."""
        return client

    connection_manager_module.async_test_connection_with_temporary_unit = (
        mock_async_test_connection_with_temporary_unit
    )
    connection_manager_module.async_get_ha_unit = mock_async_get_ha_unit
    connection_manager_module.connect_modbus_client = mock_connect_modbus_client
    connection_manager_module.ensure_modbus_connection = mock_ensure_modbus_connection
    monkeypatch.setitem(sys.modules, connection_manager_name, connection_manager_module)

    # Mock coordinator_manager module
    coordinator_manager_module = types.ModuleType(coordinator_manager_name)

    class MockCoordinatorManager:
        def __init__(self, *args, **kwargs):
            self.host = args[1] if len(args) > 1 else "192.168.1.100"
            self.port = args[2] if len(args) > 2 else 502

        def get_coordinator(self, coordinator_type):
            return types.SimpleNamespace()

        async def async_setup(self):
            pass

        async def async_shutdown(self, disconnect_clients=True):
            pass

    class MockUnifiedCoordinator:
        def __init__(self, *args, **kwargs):
            self.data = {}

        async def async_setup(self):
            pass

        async def async_shutdown(self):
            pass

    coordinator_manager_module.CoordinatorManager = MockCoordinatorManager
    coordinator_manager_module.UnifiedCoordinator = MockUnifiedCoordinator
    monkeypatch.setitem(
        sys.modules, coordinator_manager_name, coordinator_manager_module
    )

    # Mock repair module
    repair_module = types.ModuleType(repair_name)
    # Production defines these as sync functions called without await.
    repair_module.async_create_connection_issue = MagicMock()
    repair_module.async_delete_connection_issue = lambda hass, entry: None
    repair_module.async_create_abnormality_issue = MagicMock()
    repair_module.async_delete_abnormality_issue = lambda hass, entry: None
    monkeypatch.setitem(sys.modules, repair_name, repair_module)

    # Mock runtime_data module
    runtime_data_module = types.ModuleType(runtime_data_name)

    class MockRuntimeData:
        def __init__(self, coordinator, normal_coordinator, slow_coordinator, manager):
            self.coordinator = coordinator
            self.normal_coordinator = normal_coordinator
            self.slow_coordinator = slow_coordinator
            self.manager = manager

    runtime_data_module.RuntimeData = MockRuntimeData
    monkeypatch.setitem(sys.modules, runtime_data_name, runtime_data_module)

    # Mock services module
    services_module = types.ModuleType(services_name)
    services_module.register_services = lambda hass: None

    async def _noop_cancel_single_heatup(config_entry_id):
        return None

    services_module.async_cancel_single_heatup = _noop_cancel_single_heatup
    monkeypatch.setitem(sys.modules, services_name, services_module)

    return importlib.import_module(module_name)


@pytest.mark.asyncio
async def test_async_setup_entry_success(monkeypatch):
    """Test successful async_setup_entry."""
    integration_module = _load_integration_module(monkeypatch)

    # Create mock hass and entry
    hass = types.SimpleNamespace()
    hass.config_entries = types.SimpleNamespace()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_entries = lambda domain: []
    hass.data = {}

    entry = types.SimpleNamespace()
    entry.data = {"host": "192.168.1.100", "port": 502}
    entry.options = {}
    entry.entry_id = "test_entry_id"
    entry.runtime_data = None

    result = await integration_module.async_setup_entry(hass, entry)
    assert result is True
    assert hasattr(entry, "runtime_data")
    assert entry.runtime_data is not None


@pytest.mark.asyncio
async def test_async_setup_entry_connection_failure(monkeypatch):
    """Test async_setup_entry with connection failure."""
    integration_module = _load_integration_module(monkeypatch)

    # Setup probes the endpoint via async_test_connection_with_temporary_unit;
    # make that probe fail so setup raises ConfigEntryNotReady.
    connection_manager_name = (
        "custom_components.ha_daikin_altherma4_modbus.modbus.connection_manager"
    )

    async def failing_probe(hass, host, port, unit_id):
        return False, "cannot_connect"

    monkeypatch.setattr(
        sys.modules[connection_manager_name],
        "async_test_connection_with_temporary_unit",
        failing_probe,
    )

    hass = types.SimpleNamespace()
    hass.config_entries = types.SimpleNamespace()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_entries = lambda domain: []
    hass.data = {}

    entry = types.SimpleNamespace()
    entry.data = {"host": "192.168.1.100", "port": 502}
    entry.options = {}
    entry.entry_id = "test_entry_id"

    from homeassistant.exceptions import ConfigEntryNotReady

    try:
        await integration_module.async_setup_entry(hass, entry)
        assert False, "Expected ConfigEntryNotReady"
    except ConfigEntryNotReady:
        pass


@pytest.mark.asyncio
async def test_async_unload_entry(monkeypatch):
    """Test async_unload_entry."""
    integration_module = _load_integration_module(monkeypatch)

    hass = types.SimpleNamespace()
    hass.config_entries = types.SimpleNamespace()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_entries = lambda domain: []
    hass.data = {}

    entry = types.SimpleNamespace()
    entry.data = {"host": "192.168.1.100", "port": 502}
    entry.options = {}
    entry.entry_id = "test_entry_id"

    # Mock runtime_data with coordinator manager
    mock_manager = AsyncMock()
    mock_manager.async_shutdown = AsyncMock()
    mock_coordinator = types.SimpleNamespace()
    entry.runtime_data = types.SimpleNamespace(
        manager=mock_manager, coordinator=mock_coordinator
    )

    result = await integration_module.async_unload_entry(hass, entry)
    assert result is True
    mock_manager.async_shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_failure(monkeypatch):
    """Test async_unload_entry with platform unload failure."""
    integration_module = _load_integration_module(monkeypatch)

    hass = types.SimpleNamespace()
    hass.config_entries = types.SimpleNamespace()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    hass.config_entries.async_entries = lambda domain: []
    hass.data = {}

    entry = types.SimpleNamespace()
    entry.data = {"host": "192.168.1.100", "port": 502}
    entry.options = {}
    entry.entry_id = "test_entry_id"

    mock_manager = AsyncMock()
    mock_manager.async_shutdown = AsyncMock()
    mock_coordinator = types.SimpleNamespace()
    entry.runtime_data = types.SimpleNamespace(
        manager=mock_manager, coordinator=mock_coordinator
    )

    result = await integration_module.async_unload_entry(hass, entry)
    assert result is False
    mock_manager.async_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_async_reload_entry(monkeypatch):
    """Test async_reload_entry - integration doesn't have this function."""
    integration_module = _load_integration_module(monkeypatch)

    # Verify that async_reload_entry doesn't exist
    assert not hasattr(integration_module, "async_reload_entry")


@pytest.mark.asyncio
async def test_async_setup_entry_demo_mode(monkeypatch):
    """Test async_setup_entry in demo mode."""
    integration_module = _load_integration_module(monkeypatch)

    hass = types.SimpleNamespace()
    hass.config_entries = types.SimpleNamespace()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_entries = lambda domain: []
    hass.data = {}

    entry = types.SimpleNamespace()
    entry.data = {"host": "192.168.1.100", "port": 502}
    entry.options = {"demo_mode": True}
    entry.entry_id = "test_entry_id"
    entry.runtime_data = None

    result = await integration_module.async_setup_entry(hass, entry)
    assert result is True
    assert hasattr(entry, "runtime_data")
    assert entry.runtime_data is not None
