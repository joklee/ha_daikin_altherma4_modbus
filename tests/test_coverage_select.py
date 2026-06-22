"""Tests for select.py."""

from types import SimpleNamespace

import pytest

from custom_components.ha_daikin_altherma4_modbus.select import (
    DaikinSelect,
    async_setup_entry,
)
from custom_components.ha_daikin_altherma4_modbus.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.register_types import (
    INT16,
    SelectRegister,
)


def _mock_coordinator(data=None):
    c = SimpleNamespace()
    c.data = data or {}
    return c


def _mock_entry():
    coordinator = _mock_coordinator()
    runtime_data = SimpleNamespace(coordinator=coordinator)
    return SimpleNamespace(entry_id="test", data={}, options={}, runtime_data=runtime_data)


@pytest.mark.asyncio
async def test_async_setup_entry_creates_selects():
    """Test that async_setup_entry creates DaikinSelect for SelectRegister with enum_map."""
    import custom_components.ha_daikin_altherma4_modbus.select as sel_mod
    from custom_components.ha_daikin_altherma4_modbus.register_constants import (
        HOLDING_REGISTERS,
    )

    # Patch HOLDING_REGISTERS with a SelectRegister
    original = sel_mod.HOLDING_REGISTERS
    sel_mod.HOLDING_REGISTERS = [
        SelectRegister(
            name="Operation Mode",
            address=3,
            input_type="holding",
            register_name="holding_3",
            data_type=INT16,
            enum_map={0: "auto", 1: "heating", 2: "cooling"},
            entity_category="config",
            translation_key="operation_mode",
        )
    ]

    coordinator = _mock_coordinator()
    entry = _mock_entry()
    hass = SimpleNamespace()

    added = []
    try:
        await async_setup_entry(hass, entry, lambda e: added.extend(e))
        assert len(added) == 1
        assert isinstance(added[0], DaikinSelect)
    finally:
        sel_mod.HOLDING_REGISTERS = original


def test_daikin_select_init():
    """Test DaikinSelect initialization."""
    coordinator = _mock_coordinator()
    entry = _mock_entry()
    enum_map = {0: "auto", 1: "heating", 2: "cooling"}
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map=enum_map,
        entity_category="config",
        translation_key="operation_mode",
    )
    assert select_entity._attr_unique_id == f"{DOMAIN}_holding_3"
    assert select_entity._attr_options == ["auto", "heating", "cooling"]
    assert select_entity._attr_translation_key == "operation_mode"


def test_daikin_select_available_with_valid_value():
    """Test DaikinSelect available when value is in enum_map."""
    coordinator = _mock_coordinator({"holding_3": {"value": 1}})
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating", 2: "cooling"},
    )
    assert select_entity.available is True


def test_daikin_select_available_with_none_data():
    """Test DaikinSelect unavailable when data is None."""
    coordinator = _mock_coordinator({"holding_3": None})
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating"},
    )
    assert select_entity.available is False


def test_daikin_select_available_with_missing_register():
    """Test DaikinSelect unavailable when register not in data."""
    coordinator = _mock_coordinator({})
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating"},
    )
    assert select_entity.available is False


def test_daikin_select_current_option():
    """Test DaikinSelect current_option property."""
    coordinator = _mock_coordinator({"holding_3": {"value": 2}})
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating", 2: "cooling"},
    )
    assert select_entity.current_option == "cooling"


def test_daikin_select_current_option_none():
    """Test DaikinSelect current_option returns None for invalid value."""
    coordinator = _mock_coordinator({"holding_3": {"value": 999}})
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating", 2: "cooling"},
    )
    assert select_entity.current_option is None


@pytest.mark.asyncio
async def test_daikin_select_option_success():
    """Test DaikinSelect async_select_option writes to register."""
    from unittest.mock import AsyncMock

    coordinator = _mock_coordinator({"holding_3": {"value": 1}})
    coordinator.data_manager = SimpleNamespace(
        write_holding_register=AsyncMock()
    )
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating", 2: "cooling"},
    )

    await select_entity.async_select_option("cooling")
    coordinator.data_manager.write_holding_register.assert_called_once_with(
        "holding_3", 2
    )


@pytest.mark.asyncio
async def test_daikin_select_option_no_coordinator():
    """Test DaikinSelect raises when coordinator has no data_manager."""
    coordinator = _mock_coordinator()
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating"},
    )

    with pytest.raises(Exception):
        await select_entity.async_select_option("heating")


@pytest.mark.asyncio
async def test_daikin_select_option_unsupported():
    """Test DaikinSelect raises for unsupported option."""
    coordinator = _mock_coordinator()
    coordinator.data_manager = SimpleNamespace(
        write_holding_register=lambda *a, **kw: None
    )
    entry = _mock_entry()
    select_entity = DaikinSelect(
        coordinator=coordinator,
        entry=entry,
        address=3,
        register_name="holding_3",
        enum_map={0: "auto", 1: "heating"},
    )

    with pytest.raises(Exception):
        await select_entity.async_select_option("invalid_option")
