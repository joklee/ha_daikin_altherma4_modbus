import importlib
import inspect
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def _reset_modules(*names: str) -> None:
    for name in names:
        sys.modules.pop(name, None)


def _install_fake_package(monkeypatch) -> str:
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _load_integration_module(
    monkeypatch,
    *,
    manager_setup_side_effect=None,
    forward_setups_side_effect=None,
):
    package_name = _install_fake_package(monkeypatch)
    const_name = f"{package_name}.const"
    coordinator_manager_name = f"{package_name}.coordinator_manager"
    modbus_client_name = f"{package_name}.modbus_client"
    module_name = package_name

    _reset_modules(
        module_name, const_name, coordinator_manager_name, modbus_client_name
    )

    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SLOW_SCAN_INTERVAL = 600
    const_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, const_name, const_module)

    coordinator_manager_module = types.ModuleType(coordinator_manager_name)

    class FakeCoordinatorManager:
        last_instance = None

        def __init__(self, hass, host, port, normal_interval, slow_interval, demo_mode):
            self.host = host
            self.port = port
            self.normal = SimpleNamespace()
            self.slow = SimpleNamespace()
            self.async_setup = AsyncMock(side_effect=manager_setup_side_effect)
            self.async_shutdown = AsyncMock()
            FakeCoordinatorManager.last_instance = self

        def get_coordinator(self, coordinator_type):
            return self.normal if coordinator_type == "normal" else self.slow

    class FakeUnifiedCoordinator:
        last_instance = None

        def __init__(self, hass, manager, normal_coordinator, slow_coordinator):
            self.data = {}
            self.async_setup = AsyncMock()
            self.async_shutdown = AsyncMock()
            FakeUnifiedCoordinator.last_instance = self

    coordinator_manager_module.CoordinatorManager = FakeCoordinatorManager
    coordinator_manager_module.UnifiedCoordinator = FakeUnifiedCoordinator
    monkeypatch.setitem(
        sys.modules, coordinator_manager_name, coordinator_manager_module
    )

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

    integration = importlib.import_module(module_name)
    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(
                side_effect=forward_setups_side_effect
            ),
            async_entries=lambda domain: [],
        ),
    )
    entry = SimpleNamespace(
        entry_id="entry_1",
        data={"host": "192.168.1.20", "port": 502},
        options={"scan_interval": 10, "slow_scan_interval": 600, "demo_mode": False},
    )

    return (
        integration,
        hass,
        entry,
        FakeCoordinatorManager,
        FakeUnifiedCoordinator,
        FakeRealModbusTcpClient,
    )


@pytest.mark.asyncio
async def test_setup_rolls_back_on_manager_setup_failure(monkeypatch):
    (
        integration,
        hass,
        entry,
        manager_cls,
        unified_cls,
        client_cls,
    ) = _load_integration_module(
        monkeypatch, manager_setup_side_effect=RuntimeError("setup failed")
    )

    result = await integration.async_setup_entry(hass, entry)

    assert result is False
    manager = manager_cls.last_instance
    unified = unified_cls.last_instance
    manager.async_setup.assert_awaited_once()
    unified.async_setup.assert_awaited_once()
    unified.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)
    client_cls.async_close_cached_client.assert_awaited_once_with("192.168.1.20", 502)
    hass.config_entries.async_forward_entry_setups.assert_not_awaited()
    assert "ha_daikin_altherma4_modbus" not in hass.data


@pytest.mark.asyncio
async def test_setup_rolls_back_on_forward_setups_failure(monkeypatch):
    (
        integration,
        hass,
        entry,
        manager_cls,
        unified_cls,
        client_cls,
    ) = _load_integration_module(
        monkeypatch, forward_setups_side_effect=RuntimeError("forward failed")
    )

    result = await integration.async_setup_entry(hass, entry)

    assert result is False
    manager = manager_cls.last_instance
    unified = unified_cls.last_instance
    manager.async_setup.assert_awaited_once()
    unified.async_setup.assert_awaited_once()
    unified.async_shutdown.assert_awaited_once()
    manager.async_shutdown.assert_awaited_once_with(disconnect_clients=True)
    client_cls.async_close_cached_client.assert_awaited_once_with("192.168.1.20", 502)
    hass.config_entries.async_forward_entry_setups.assert_awaited_once()
    assert "ha_daikin_altherma4_modbus" not in hass.data


def _load_switch_module(monkeypatch):
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.switch"
    const_name = f"{package_name}.const"

    _reset_modules(
        module_name,
        const_name,
        "homeassistant.components.switch",
        "homeassistant.helpers.update_coordinator",
    )

    switch_component_module = types.ModuleType("homeassistant.components.switch")
    switch_component_module.SwitchEntity = object
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.switch", switch_component_module
    )

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class FakeCoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    update_coordinator_module.CoordinatorEntity = FakeCoordinatorEntity
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator_module,
    )

    # Mock homeassistant.exceptions
    exceptions_module = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions_module.HomeAssistantError = HomeAssistantError
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions_module)

    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.COIL_SENSORS = []
    const_module.COIL_DEVICE_INFO = {}
    const_module.COIL_REGISTERS = []
    const_module.HOLDING_SWITCHES = []
    const_module.HOLDING_DEVICE_INFO = {}
    monkeypatch.setitem(sys.modules, const_name, const_module)

    module = importlib.import_module(module_name)
    # Attach HomeAssistantError to module so tests can access it
    module.HomeAssistantError = exceptions_module.HomeAssistantError
    return module


@pytest.mark.asyncio
async def test_switch_propagates_unexpected_exception(monkeypatch):
    switch_module = _load_switch_module(monkeypatch)
    coordinator = SimpleNamespace(
        data={},
        data_manager=SimpleNamespace(
            write_coil_register=AsyncMock(side_effect=RuntimeError("unexpected"))
        ),
    )
    entity = switch_module.DaikinCoilSwitch(
        coordinator=coordinator,
        entry=SimpleNamespace(),
        address=1,
        register_name="coil_1",
    )

    # RuntimeError is now wrapped in HomeAssistantError by safe_write_register
    with pytest.raises(switch_module.HomeAssistantError):
        await entity.async_turn_on()


@pytest.mark.asyncio
async def test_switch_handles_daikin_modbus_exception(monkeypatch):
    switch_module = _load_switch_module(monkeypatch)

    # Create exceptions module mock with DaikinModbusException
    exceptions_module = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions_module.HomeAssistantError = HomeAssistantError
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions_module)

    # Create a local DaikinModbusException for the test
    class DaikinModbusException(Exception):
        pass

    coordinator = SimpleNamespace(
        data={},
        data_manager=SimpleNamespace(
            write_holding_register=AsyncMock(side_effect=DaikinModbusException("known"))
        ),
    )
    entity = switch_module.DaikinHoldingSwitch(
        coordinator=coordinator,
        entry=SimpleNamespace(),
        address=4,
        register_name="holding_4",
    )

    with pytest.raises(HomeAssistantError):
        await entity.async_turn_on()


@pytest.mark.asyncio
async def test_holding_switch_uses_enum_on_off_values(monkeypatch):
    switch_module = _load_switch_module(monkeypatch)
    coordinator = SimpleNamespace(
        data={"holding_4": {"value": 20}},
        data_manager=SimpleNamespace(
            write_holding_register=AsyncMock(return_value=True)
        ),
    )
    entity = switch_module.DaikinHoldingSwitch(
        coordinator=coordinator,
        entry=SimpleNamespace(),
        address=4,
        register_name="holding_4",
        enum_map={10: "Off", 20: "On"},
    )

    assert entity.is_on is True
    await entity.async_turn_on()
    coordinator.data_manager.write_holding_register.assert_awaited_with("holding_4", 20)

    await entity.async_turn_off()
    coordinator.data_manager.write_holding_register.assert_awaited_with("holding_4", 10)


def _load_select_module(monkeypatch):
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.select"
    const_name = f"{package_name}.const"

    _reset_modules(
        module_name,
        const_name,
        "homeassistant.components.select",
        "homeassistant.helpers.update_coordinator",
        "homeassistant.exceptions",
    )

    select_component_module = types.ModuleType("homeassistant.components.select")
    select_component_module.SelectEntity = object
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.select", select_component_module
    )

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class FakeCoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    update_coordinator_module.CoordinatorEntity = FakeCoordinatorEntity
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator_module,
    )

    exceptions_module = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions_module.HomeAssistantError = HomeAssistantError
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions_module)

    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SELECT_REGISTERS = []
    const_module.HOLDING_SELECT_REGISTERS = []
    const_module.HOLDING_DEVICE_INFO = {}
    monkeypatch.setitem(sys.modules, const_name, const_module)

    return importlib.import_module(module_name)


@pytest.mark.asyncio
async def test_select_rejects_unsupported_option(monkeypatch):
    select_module = _load_select_module(monkeypatch)
    coordinator = SimpleNamespace(
        data={"holding_56": {"value": 0}},
        data_manager=SimpleNamespace(
            write_holding_register=AsyncMock(return_value=True)
        ),
    )
    entity = select_module.DaikinSelect(
        coordinator=coordinator,
        entry=SimpleNamespace(),
        address=56,
        register_name="holding_56",
        enum_map={0: "Free running", 1: "Forced off"},
    )

    with pytest.raises(select_module.HomeAssistantError):
        await entity.async_select_option("Not a valid option")


def _load_transport_session_module(monkeypatch, ensure_side_effect):
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.transport_session"
    connection_manager_name = f"{package_name}.connection_manager"

    _reset_modules(module_name, connection_manager_name)

    connection_manager_module = types.ModuleType(connection_manager_name)
    ensure_mock = AsyncMock(side_effect=ensure_side_effect)
    connection_manager_module.ensure_modbus_connection = ensure_mock
    monkeypatch.setitem(sys.modules, connection_manager_name, connection_manager_module)

    module = importlib.import_module(module_name)
    return module, ensure_mock


@pytest.mark.asyncio
async def test_transport_session_reraises_unexpected_errors(monkeypatch):
    transport_module, _ = _load_transport_session_module(
        monkeypatch, RuntimeError("unexpected")
    )
    session = transport_module.ModbusTransportSession(
        "192.168.1.20", 502, demo_mode=False
    )

    with pytest.raises(RuntimeError):
        await session.ensure_connection()


def _load_connection_manager_module(monkeypatch):
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.connection_manager"
    modbus_client_name = f"{package_name}.modbus_client"
    mock_client_name = f"{package_name}.mock_client"
    client_interface_name = f"{package_name}.client_interface"
    _reset_modules(
        module_name, modbus_client_name, mock_client_name, client_interface_name
    )

    modbus_client_module = types.ModuleType(modbus_client_name)
    modbus_client_module.RealModbusTcpClient = object
    monkeypatch.setitem(sys.modules, modbus_client_name, modbus_client_module)

    mock_client_module = types.ModuleType(mock_client_name)
    mock_client_module.MockModbusTcpClient = object
    monkeypatch.setitem(sys.modules, mock_client_name, mock_client_module)

    client_interface_module = types.ModuleType(client_interface_name)
    client_interface_module.ModbusClientInterface = object
    monkeypatch.setitem(sys.modules, client_interface_name, client_interface_module)

    return importlib.import_module(module_name)


def test_connection_manager_has_no_artificial_sleep_after_connect(monkeypatch):
    module = _load_connection_manager_module(monkeypatch)
    source = inspect.getsource(module.connect_modbus_client)
    assert "sleep(" not in source
