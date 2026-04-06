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
        Path(__file__).resolve().parents[1]
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
    module_name = f"{package_name}.number"
    const_name = f"{package_name}.const"
    common_name = f"{package_name}.common"

    _reset_modules(
        module_name,
        const_name,
        common_name,
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

    # Mock common module
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
    monkeypatch.setitem(sys.modules, common_name, common_module)

    # Mock const module
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.HOLDING_DEVICE_INFO = {"name": "Test Device"}

    # Create mock holding registers
    class MockRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    const_module.HOLDING_REGISTERS = [
        MockRegister(
            address=1,
            min_value=0,
            max_value=100,
            step=1,
            unit="°C",
            scale=1,
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
            scale=1,
            register_name="holding_2",
            enum_map={0: "Off", 1: "Low", 2: "Medium", 3: "High", 4: "Auto"},
            entity_category="config",
            translation_key="mode_select",
        ),
    ]
    monkeypatch.setitem(sys.modules, const_name, const_module)

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
        scale=0.1,
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
        scale=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    assert entity.available is True


def test_daikin_number_native_value_with_data_scale(monkeypatch):
    """Test native_value when data has scale stored."""
    number_module = _load_number_module(monkeypatch)

    coordinator = SimpleNamespace(data={"holding_1": {"value": 250, "scale": 0.1}})
    entry = SimpleNamespace()

    entity = number_module.DaikinNumber(
        coordinator=coordinator,
        entry=entry,
        address=1,
        min_v=0,
        max_v=100,
        step=1,
        unit="°C",
        scale=0.1,
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
        scale=0.1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    # Value should be scaled: 250 * 0.1 = 25.0
    assert entity.native_value == 25.0


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
        scale=1,
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
        scale=1,
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
        scale=1,
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
        scale=1,
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
        scale=1,
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
        scale=1,
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
        scale=0.1,
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
        scale=1,
        register_name="holding_1",
        enum_map=None,
        entity_category=None,
        translation_key=None,
    )

    await entity.async_set_native_value(-10)

    # Verify write was called via safe_write_register mock
    from custom_components.ha_daikin_altherma4_modbus.common import safe_write_register

    safe_write_register.assert_awaited_once()
