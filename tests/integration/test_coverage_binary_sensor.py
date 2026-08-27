"""Tests for binary_sensor.py - target >95% coverage."""

from types import SimpleNamespace

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.core.register_constants import (
    DISCRETE_INPUT_DEVICE_INFO,
    INPUT_DEVICE_INFO,
)
from custom_components.ha_daikin_altherma4_modbus.entities.binary_sensor import (
    DaikinBinarySensor,
    DaikinDiscreteInputSensor,
    async_setup_entry,
)


def _mock_coordinator(data=None):
    c = SimpleNamespace()
    c.data = data or {}
    return c


def _mock_entry():
    coordinator = _mock_coordinator()
    runtime_data = SimpleNamespace(coordinator=coordinator)
    return SimpleNamespace(
        entry_id="test", data={}, options={}, runtime_data=runtime_data
    )


@pytest.mark.asyncio
async def test_async_setup_entry_creates_binary_sensors():
    """Test that async_setup_entry creates DaikinBinarySensor for running/problem device_class."""
    entry = _mock_entry()
    hass = SimpleNamespace()
    hass.config_entries = SimpleNamespace(async_entries=lambda domain: [])

    added = []

    def add_entities(entities):
        added.extend(entities)

    await async_setup_entry(hass, entry, add_entities)

    # Should have created entities from INPUT_REGISTERS with running/problem device_class
    # plus discrete input sensors
    assert len(added) > 0
    binary_sensors = [e for e in added if isinstance(e, DaikinBinarySensor)]
    discrete_sensors = [e for e in added if isinstance(e, DaikinDiscreteInputSensor)]
    assert len(binary_sensors) > 0
    assert len(discrete_sensors) > 0


@pytest.mark.asyncio
async def test_async_setup_entry_returns_on_no_coordinator():
    """Test that async_setup_entry returns early if coordinator is None."""
    entry = _mock_entry()
    hass = SimpleNamespace()
    hass.config_entries = SimpleNamespace(async_entries=lambda domain: [])

    # Patch get_coordinator_from_entry to return None
    import custom_components.ha_daikin_altherma4_modbus.entities.binary_sensor as bs_mod

    original = bs_mod.get_coordinator_from_entry
    bs_mod.get_coordinator_from_entry = lambda *a: None

    added = []
    try:
        await async_setup_entry(hass, entry, lambda e: added.extend(e))
        assert len(added) == 0
    finally:
        bs_mod.get_coordinator_from_entry = original


def test_daikin_binary_sensor_init():
    """Test DaikinBinarySensor initialization."""
    coordinator = _mock_coordinator()
    entry = _mock_entry()
    sensor = DaikinBinarySensor(
        coordinator=coordinator,
        entry=entry,
        address=30,
        device_class="running",
        register_name="input_30",
        entity_category="diagnostic",
        unique_id="test_id",
        translation_key="input_30",
    )
    assert sensor._attr_unique_id == "test_id"
    assert sensor._attr_device_class == "running"
    assert sensor._attr_device_info == INPUT_DEVICE_INFO
    assert sensor._attr_translation_key == "input_30"


def test_daikin_binary_sensor_init_default_unique_id():
    """Test DaikinBinarySensor with default unique_id."""
    coordinator = _mock_coordinator()
    entry = _mock_entry()
    sensor = DaikinBinarySensor(
        coordinator=coordinator,
        entry=entry,
        address=30,
        device_class="running",
        register_name="input_30",
    )
    assert sensor._attr_unique_id == f"{DOMAIN}_input_30"


def test_daikin_binary_sensor_available():
    """Test DaikinBinarySensor availability."""
    coordinator = _mock_coordinator({"input_30": {"value": 1}})
    entry = _mock_entry()
    sensor = DaikinBinarySensor(
        coordinator=coordinator,
        entry=entry,
        address=30,
        device_class="running",
        register_name="input_30",
    )
    assert sensor.available is True


def test_daikin_binary_sensor_unavailable():
    """Test DaikinBinarySensor unavailable when register not in data."""
    coordinator = _mock_coordinator({})
    entry = _mock_entry()
    sensor = DaikinBinarySensor(
        coordinator=coordinator,
        entry=entry,
        address=30,
        device_class="running",
        register_name="input_30",
    )
    assert sensor.available is False


def test_daikin_binary_sensor_is_on():
    """Test DaikinBinarySensor is_on property."""
    coordinator = _mock_coordinator({"input_30": {"value": 1}})
    entry = _mock_entry()
    sensor = DaikinBinarySensor(
        coordinator=coordinator,
        entry=entry,
        address=30,
        device_class="running",
        register_name="input_30",
    )
    assert sensor.is_on is True


def test_daikin_binary_sensor_is_off():
    """Test DaikinBinarySensor is_on=False when value is 0."""
    coordinator = _mock_coordinator({"input_30": {"value": 0}})
    entry = _mock_entry()
    sensor = DaikinBinarySensor(
        coordinator=coordinator,
        entry=entry,
        address=30,
        device_class="running",
        register_name="input_30",
    )
    assert sensor.is_on is False


def test_daikin_binary_sensor_is_on_none_data():
    """Test DaikinBinarySensor is_on=False when data is None."""
    coordinator = _mock_coordinator({"input_30": None})
    entry = _mock_entry()
    sensor = DaikinBinarySensor(
        coordinator=coordinator,
        entry=entry,
        address=30,
        device_class="running",
        register_name="input_30",
    )
    assert sensor.is_on is False


def test_daikin_discrete_input_sensor_init():
    """Test DaikinDiscreteInputSensor initialization."""
    coordinator = _mock_coordinator()
    entry = _mock_entry()
    sensor = DaikinDiscreteInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=1,
        device_class="running",
        register_name="discrete_1",
        entity_category="diagnostic",
        unique_id="test_discrete",
        translation_key="discrete_1",
    )
    assert sensor._attr_unique_id == "test_discrete"
    assert sensor._attr_device_class == "running"
    assert sensor._attr_device_info == DISCRETE_INPUT_DEVICE_INFO


def test_daikin_discrete_input_sensor_init_default_unique_id():
    """Test DaikinDiscreteInputSensor with default unique_id."""
    coordinator = _mock_coordinator()
    entry = _mock_entry()
    sensor = DaikinDiscreteInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=1,
        device_class="running",
        register_name="discrete_1",
    )
    assert sensor._attr_unique_id == f"{DOMAIN}_discrete_1"


def test_daikin_discrete_input_sensor_available():
    """Test DaikinDiscreteInputSensor availability."""
    coordinator = _mock_coordinator({"discrete_1": {"value": 1}})
    entry = _mock_entry()
    sensor = DaikinDiscreteInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=1,
        device_class="running",
        register_name="discrete_1",
    )
    assert sensor.available is True


def test_daikin_discrete_input_sensor_unavailable():
    """Test DaikinDiscreteInputSensor unavailable."""
    coordinator = _mock_coordinator({})
    entry = _mock_entry()
    sensor = DaikinDiscreteInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=1,
        device_class="running",
        register_name="discrete_1",
    )
    assert sensor.available is False


def test_daikin_discrete_input_sensor_is_on():
    """Test DaikinDiscreteInputSensor is_on property."""
    coordinator = _mock_coordinator({"discrete_11": {"value": 1}})
    entry = _mock_entry()
    sensor = DaikinDiscreteInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=11,
        device_class="running",
        register_name="discrete_11",
    )
    assert sensor.is_on is True


def test_daikin_discrete_input_sensor_is_off():
    """Test DaikinDiscreteInputSensor is_on=False when value is 0."""
    coordinator = _mock_coordinator({"discrete_11": {"value": 0}})
    entry = _mock_entry()
    sensor = DaikinDiscreteInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=11,
        device_class="running",
        register_name="discrete_11",
    )
    assert sensor.is_on is False


def test_daikin_discrete_input_sensor_is_on_none_data():
    """Test DaikinDiscreteInputSensor is_on=False when data is None."""
    coordinator = _mock_coordinator({"discrete_11": None})
    entry = _mock_entry()
    sensor = DaikinDiscreteInputSensor(
        coordinator=coordinator,
        entry=entry,
        address=11,
        device_class="running",
        register_name="discrete_11",
    )
    assert sensor.is_on is False
