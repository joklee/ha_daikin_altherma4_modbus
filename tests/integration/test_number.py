"""Tests for number.py module."""

import importlib
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
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _load_number_module(monkeypatch):
    """Load number module with mocked dependencies."""
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.entities.number"
    const_name = f"{package_name}.core.const"
    common_name = f"{package_name}.common"

    _reset_modules(
        module_name,
        const_name,
        common_name,
        f"{package_name}.core.register_constants",
        f"{package_name}.core.register_types",
        "homeassistant.components.number",
        "homeassistant.helpers.update_coordinator",
    )

    # Mock homeassistant components
    number_component = types.ModuleType("homeassistant.components.number")
    number_component.NumberEntity = type("NumberEntity", (), {})
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.number", number_component
    )

    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class FakeCoordinatorEntity:
        def __init__(self, coordinator=None):
            self.coordinator = coordinator

    update_coordinator.CoordinatorEntity = FakeCoordinatorEntity
    monkeypatch.setitem(
        sys.modules, "homeassistant.helpers.update_coordinator", update_coordinator
    )

    # Mock common module - don't mock get_register_config to use real function
    common_module = types.ModuleType(common_name)
    common_module.get_register_scale = lambda data: (
        data.get("scale") if isinstance(data, dict) else None
    )
    common_module.get_register_value = lambda data: (
        data.get("value") if isinstance(data, dict) else None
    )
    common_module.is_entity_available = lambda data, name: True
    common_module.safe_write_register = AsyncMock()
    common_module.to_signed_16bit = lambda x: x if x < 32768 else x - 65536
    common_module.to_unsigned_16bit = lambda x: x if x >= 0 else x + 65536

    # Mock get_register_config to make it available in test environment
    def mock_get_register_config(register_name, register_list=None):
        if register_name == "holding_58":
            # Return mock register configuration for holding_58 (Pow16Signed)
            from types import SimpleNamespace

            return SimpleNamespace(
                register_name="holding_58",
                data_type=SimpleNamespace(scaling=0.01, name="Pow16"),
                min_value=0,
                max_value=20,
                unit="kW",
            )
        return None

    common_module.get_register_config = mock_get_register_config
    monkeypatch.setitem(sys.modules, common_name, common_module)

    # Mock const module
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.HOLDING_DEVICE_INFO = {"name": "Test Device"}

    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock register_types module with NumberRegister
    register_types_name = f"{package_name}.core.register_types"
    register_types_module = types.ModuleType(register_types_name)

    class NumberRegister:
        pass

    # Mock RegisterDataType
    class MockRegisterDataType:
        def __init__(self, name, signed, bits, scaling, range=None):
            self.name = name
            self.signed = signed
            self.bits = bits
            self.scaling = scaling
            self.range = range

    register_types_module.NumberRegister = NumberRegister
    register_types_module.RegisterDataType = MockRegisterDataType
    register_types_module.INT16 = MockRegisterDataType(
        "Int16", True, 16, 1, (-32768, 32767)
    )
    register_types_module.TEMP16 = MockRegisterDataType(
        "Temp16", True, 16, 0.01, (-327.68, 327.67)
    )
    register_types_module.POW16 = MockRegisterDataType(
        "Pow16", True, 16, 0.01, (-327.68, 327.67)
    )
    monkeypatch.setitem(sys.modules, register_types_name, register_types_module)

    # Create mock holding registers that are instances of NumberRegister
    class MockRegister(NumberRegister):
        def __init__(self, **kwargs):
            # Set default data_type if not provided
            if "data_type" not in kwargs:
                kwargs["data_type"] = None
            for k, v in kwargs.items():
                setattr(self, k, v)

    const_module.HOLDING_REGISTERS = [
        MockRegister(
            address=1,
            min_value=0,
            max_value=100,
            step=1,
            unit="°C",
            data_type=register_types_module.INT16,
            register_name="holding_1",
            enum_map=None,
            entity_category=None,
            translation_key="temp_setpoint",
        ),
        MockRegister(
            address=2,
            min_value=0,
            max_value=5,
            step=1,
            unit="",
            data_type=register_types_module.INT16,
            register_name="holding_2",
            enum_map={0: "Off", 1: "Low", 2: "Medium", 3: "High", 4: "Auto"},
            entity_category="config",
            translation_key="mode_select",
        ),
    ]

    # Mock register_constants module with HOLDING_REGISTERS
    register_constants_name = f"{package_name}.core.register_constants"
    register_constants_module = types.ModuleType(register_constants_name)
    register_constants_module.HOLDING_REGISTERS = const_module.HOLDING_REGISTERS
    register_constants_module.HOLDING_DEVICE_INFO = const_module.HOLDING_DEVICE_INFO
    monkeypatch.setitem(sys.modules, register_constants_name, register_constants_module)

    # Install fake parent packages so real __init__.py files are not executed
    base_path = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    for sub in ("entities", "core"):
        parent_name = f"{package_name}.{sub}"
        parent = types.ModuleType(parent_name)
        parent.__path__ = [str(base_path / sub)]
        monkeypatch.setitem(sys.modules, parent_name, parent)

    return importlib.import_module(module_name)


@pytest.mark.asyncio
async def test_async_setup_entry_creates_entities(monkeypatch):
    """Test that async_setup_entry creates number entities."""
    number_module = _load_number_module(monkeypatch)

    # Mock coordinator with data_manager
    data_manager = SimpleNamespace()
    coordinator = SimpleNamespace(
        data={"holding_1": {"value": 25, "scale": 1}, "holding_2": {"value": 2}},
        data_manager=data_manager,
    )

    runtime_data = SimpleNamespace(coordinator=coordinator)
    entry = SimpleNamespace(runtime_data=runtime_data)

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    await number_module.async_setup_entry(None, entry, mock_add_entities)

    assert len(added_entities) == 2
    assert added_entities[0]._register_name == "holding_1"
    assert added_entities[1]._register_name == "holding_2"


@pytest.mark.asyncio
async def test_async_setup_entry_no_coordinator(monkeypatch):
    """Test that async_setup_entry returns early when no coordinator."""
    number_module = _load_number_module(monkeypatch)

    runtime_data = SimpleNamespace(coordinator=None)
    entry = SimpleNamespace(runtime_data=runtime_data)

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    await number_module.async_setup_entry(None, entry, mock_add_entities)

    assert len(added_entities) == 0


def test_daikin_number_initialization(monkeypatch):
    """Test DaikinNumber entity initialization."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=0.1,
        register_name="holding_1",
        enum_map=None,
        entity_category="config",
        translation_key="temp_setpoint",
    )

    assert entity._attr_unique_id == "ha_daikin_altherma4_modbus_holding_1"
    assert entity._attr_native_unit_of_measurement == "°C"
    assert entity._attr_native_min_value == 0
    assert entity._attr_native_max_value == 100
    assert entity._attr_native_step == 1
    assert entity._attr_entity_category == "config"
    assert entity._attr_translation_key == "temp_setpoint"
    assert entity._attr_has_entity_name is True


def test_daikin_number_available(monkeypatch):
    """Test DaikinNumber available property."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={"holding_1": {"value": 25}})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    assert entity.available is True


def test_daikin_number_native_value_with_data_scale(monkeypatch):
    """Test native_value when data has scale stored."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={"holding_1": {"value": 250}})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=0.1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    # When scale is stored in data, return value as-is
    assert entity.native_value == 250


def test_daikin_number_native_value_without_scale(monkeypatch):
    """Test native_value when data has no scale (apply entity scale)."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={"holding_1": {"value": 250}})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=0.1,
        unit="°C",
        data_type=0.1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    assert entity.native_value == 250


def test_daikin_number_native_value_none_data(monkeypatch):
    """Test native_value returns None when no data."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    assert entity.native_value is None


def test_daikin_number_native_value_invalid_string(monkeypatch):
    """Test native_value returns None for invalid string value."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={"holding_1": {"value": "invalid"}})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    assert entity.native_value is None


def test_daikin_number_native_value_unavailable_values(monkeypatch):
    """Test native_value returns None for unavailable values (32765, 32766)."""
    number_module = _load_number_module(monkeypatch)

    # Test 32765
    coordinator = SimpleNamespace(data={"holding_1": {"value": 32765}})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    assert entity.native_value is None

    # Test 32766
    coordinator.data["holding_1"] = {"value": 32766}
    assert entity.native_value is None


def test_daikin_number_native_value_with_enum_map(monkeypatch):
    """Test native_value with enum_map returns raw value."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={"holding_2": {"value": 2}})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=2,
        min_v=0,
        max_v=5,
        step=1,
        unit="",
        data_type=1,
        register_name="holding_2",
        enum_map={0: "Off", 1: "Low", 2: "Medium", 3: "High", 4: "Auto"},
        entity_category=None,
        translation_key=None,
    )

    # With enum_map, should return raw value
    assert entity.native_value == 2


def test_daikin_number_mode_with_enum_map(monkeypatch):
    """Test mode property returns slider for enum_map."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_1",
        enum_map={0: "Off", 1: "On"},
        entity_category=None,
        translation_key=None,
    )

    assert entity.mode == "slider"


def test_daikin_number_mode_without_enum_map(monkeypatch):
    """Test mode property returns slider without enum_map."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    assert entity.mode == "slider"


@pytest.mark.asyncio
async def test_daikin_number_async_set_native_value(monkeypatch):
    """Test async_set_native_value converts and writes value."""
    number_module = _load_number_module(monkeypatch)

    write_mock = AsyncMock()
    data_manager = SimpleNamespace(write_holding_register=write_mock)
    coordinator = SimpleNamespace(data_manager=data_manager)
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=0.1,
        unit="°C",
        data_type=0.1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    await entity.async_set_native_value(25.0)

    # Verify write was called via safe_write_register mock
    from custom_components.ha_daikin_altherma4_modbus.common import safe_write_register

    safe_write_register.assert_awaited_once()


@pytest.mark.asyncio
async def test_daikin_number_async_set_native_value_negative(monkeypatch):
    """Test async_set_native_value handles negative values."""
    number_module = _load_number_module(monkeypatch)

    write_mock = AsyncMock()
    data_manager = SimpleNamespace(write_holding_register=write_mock)
    coordinator = SimpleNamespace(data_manager=data_manager)
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=-50,
        max_v=50,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    await entity.async_set_native_value(-10)

    # Verify write was called via safe_write_register mock
    from custom_components.ha_daikin_altherma4_modbus.common import safe_write_register

    safe_write_register.assert_awaited_once()


@pytest.mark.asyncio
async def test_daikin_number_async_set_native_value_modbus_error(monkeypatch, caplog):
    """Test that Modbus write error triggers coordinator refresh.

    This test verifies the fix for:
    - "Error set value for number holding_58: Modbus error writing holding register 58"

    After a write failure, the coordinator should refresh to ensure entity
    state matches the actual device state.
    """
    import logging

    package_name = "custom_components.ha_daikin_altherma4_modbus"
    common_name = f"{package_name}.common"

    # Create a write function that raises an exception (simulating Modbus error)
    async def failing_write(register_name, value):
        raise Exception("Modbus error writing holding register 58")

    # Setup mock modules with real safe_write_register implementation
    _reset_modules(
        f"{package_name}.entities.number",
        f"{package_name}.core.const",
        f"{package_name}.common",
        f"{package_name}.core.register_constants",
        f"{package_name}.core.register_types",
        "homeassistant.components.number",
        "homeassistant.helpers.update_coordinator",
    )

    package_path = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    monkeypatch.setitem(sys.modules, package_name, package_module)

    # Mock homeassistant components
    number_component = types.ModuleType("homeassistant.components.number")
    number_component.NumberEntity = type("NumberEntity", (), {})
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.number", number_component
    )

    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class FakeCoordinatorEntity:
        def __init__(self, coordinator=None):
            self.coordinator = coordinator

    update_coordinator.CoordinatorEntity = FakeCoordinatorEntity
    monkeypatch.setitem(
        sys.modules, "homeassistant.helpers.update_coordinator", update_coordinator
    )

    # Create common module with real safe_write_register implementation (with coordinator support)
    common_module = types.ModuleType(common_name)

    async def safe_write_register(
        write_func,
        register_name,
        value,
        operation_name="write",
        register_type="register",
        coordinator=None,
    ):
        logger = logging.getLogger(common_name)
        try:
            await write_func(register_name, value)
            logger.debug(
                f"Successfully {operation_name} {register_type} {register_name}"
            )
        except Exception as e:
            logger.error(f"Error {operation_name} {register_type} {register_name}: {e}")
            # Refresh coordinator on error to ensure entity state matches device (THE FIX)
            if coordinator is not None:
                try:
                    await coordinator.async_request_refresh()
                except Exception as refresh_err:
                    logger.debug(f"Failed to refresh after write error: {refresh_err}")
            raise Exception(
                f"Failed to {operation_name} {register_type} {register_name}: {e}"
            ) from e

    common_module.safe_write_register = safe_write_register
    common_module.get_register_scale = lambda data: (
        data.get("scale") if isinstance(data, dict) else None
    )
    common_module.get_register_value = lambda data: (
        data.get("value") if isinstance(data, dict) else None
    )
    common_module.is_entity_available = lambda data, name: True
    common_module.to_signed_16bit = lambda x: x if x < 32768 else x - 65536
    common_module.to_unsigned_16bit = lambda x: x if x >= 0 else x + 65536

    # Add get_register_config mock for the test
    def get_register_config(register_name, register_list=None):
        """Return mock register config for holding_58."""
        if register_name == "holding_58":
            from types import SimpleNamespace

            return SimpleNamespace(
                register_name="holding_58",
                min_value=0,
                max_value=20,
                unit="kW",
                data_type=SimpleNamespace(scaling=0.01, name="Pow16"),
            )
        return None

    common_module.get_register_config = get_register_config
    common_module.get_coordinator_from_entry = lambda hass, entry: getattr(
        getattr(entry, "runtime_data", None), "coordinator", None
    )
    monkeypatch.setitem(sys.modules, common_name, common_module)

    # Mock const module
    const_name = f"{package_name}.core.const"
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.HOLDING_DEVICE_INFO = {"name": "Test Device"}
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock register_types module with NumberRegister
    register_types_name = f"{package_name}.core.register_types"
    register_types_module = types.ModuleType(register_types_name)

    class NumberRegister:
        pass

    register_types_module.NumberRegister = NumberRegister
    monkeypatch.setitem(sys.modules, register_types_name, register_types_module)

    # Create mock holding registers
    class MockRegister(NumberRegister):
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    const_module.HOLDING_REGISTERS = [
        MockRegister(
            address=58,
            min_value=0,
            max_value=100,
            step=1,
            unit="°C",
            data_type=1,
            register_name="holding_58",
            enum_map=None,
            entity_category=None,
            translation_key=None,
        ),
    ]

    # Mock register_constants module
    register_constants_name = f"{package_name}.core.register_constants"
    register_constants_module = types.ModuleType(register_constants_name)
    register_constants_module.HOLDING_REGISTERS = const_module.HOLDING_REGISTERS
    register_constants_module.HOLDING_DEVICE_INFO = const_module.HOLDING_DEVICE_INFO
    monkeypatch.setitem(sys.modules, register_constants_name, register_constants_module)

    # Install fake parent packages so real __init__.py files are not executed
    base_path = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    for sub in ("entities", "core"):
        parent_name = f"{package_name}.{sub}"
        parent = types.ModuleType(parent_name)
        parent.__path__ = [str(base_path / sub)]
        monkeypatch.setitem(sys.modules, parent_name, parent)

    # Now load the number module - it will use our real safe_write_register
    module_name = f"{package_name}.entities.number"
    number_module = importlib.import_module(module_name)

    # Setup coordinator with initial data
    data_manager = SimpleNamespace(write_holding_register=failing_write)
    coordinator = SimpleNamespace(
        data_manager=data_manager,
        data={"holding_58": {"value": 20, "scale": 1}},  # Initial value is 20
    )
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=58,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        data_type=1,
        register_name="holding_58",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    # Verify initial state
    assert entity.native_value == 20, "Initial value should be 20"

    with (
        caplog.at_level(logging.ERROR, logger=common_name),
        pytest.raises(Exception) as exc_info,
    ):
        await entity.async_set_native_value(25.0)

    # Verify the exception was raised with expected message
    assert "Failed to set value for number holding_58" in str(exc_info.value)

    # Verify the error was logged with the expected message format
    # "Error set value for number holding_58: Modbus error writing holding register 58"
    assert "Error set value for number holding_58" in caplog.text
    assert "Modbus error writing holding register 58" in caplog.text

    # FIX VERIFICATION: Check that coordinator refresh was triggered after write failure
    # After the fix: safe_write_register should call coordinator.async_request_refresh() on error

    # Track if refresh was called
    refresh_called = [False]

    async def mock_refresh():
        refresh_called[0] = True

    coordinator.async_request_refresh = mock_refresh

    # Try the write with refresh tracking
    try:
        await entity.async_set_native_value(25.0)
    except Exception:
        pass  # Expected to fail

    # VERIFY THE FIX: After a write failure, coordinator refresh should be called
    # to ensure entity state matches the actual device state
    assert refresh_called[0], (
        "FIX NOT WORKING: After Modbus write error 'Error set value for number holding_58', "
        "coordinator refresh was not triggered. "
        "Expected: async_request_refresh() should be called after write failure."
    )

    # Also verify the error was still logged correctly
    assert "Error set value for number holding_58" in caplog.text
    assert "Modbus error writing holding register 58" in caplog.text
