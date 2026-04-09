"""Tests for CalculatedCoPSensor."""

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace


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
    package_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _install_common_homeassistant_stubs(monkeypatch) -> None:
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []  # Make it a package
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)

    const_module = types.ModuleType("homeassistant.const")
    const_module.CONF_HOST = "host"
    const_module.CONF_PORT = "port"
    const_module.EntityCategory = SimpleNamespace(DIAGNOSTIC="diagnostic")
    monkeypatch.setitem(sys.modules, "homeassistant.const", const_module)

    core_module = types.ModuleType("homeassistant.core")
    core_module.HomeAssistant = object
    core_module.Event = object
    monkeypatch.setitem(sys.modules, "homeassistant.core", core_module)

    helpers_module = types.ModuleType("homeassistant.helpers")
    helpers_module.__path__ = []  # Make it a package
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers_module)

    restore_state_module = types.ModuleType("homeassistant.helpers.restore_state")
    restore_state_module.RestoreEntity = type("RestoreEntity", (), {})
    monkeypatch.setitem(
        sys.modules, "homeassistant.helpers.restore_state", restore_state_module
    )

    update_coordinator_module = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class FakeDataUpdateCoordinator:
        def __init__(self, hass, logger, name, update_interval):
            self.hass = hass
            self.data = {}

        async def async_config_entry_first_refresh(self):
            return None

        async def async_request_refresh(self):
            return None

        def async_add_listener(self, callback):
            return lambda: None

        def async_set_updated_data(self, data):
            self.data = data

    class FakeCoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

        async def async_added_to_hass(self):
            return None

    update_coordinator_module.DataUpdateCoordinator = FakeDataUpdateCoordinator
    update_coordinator_module.CoordinatorEntity = FakeCoordinatorEntity
    update_coordinator_module.UpdateFailed = Exception
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator_module,
    )

    components_module = types.ModuleType("homeassistant.components")
    monkeypatch.setitem(sys.modules, "homeassistant.components", components_module)

    sensor_component_module = types.ModuleType("homeassistant.components.sensor")
    sensor_component_module.SensorEntity = type("FakeSensorEntity", (), {})
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.sensor", sensor_component_module
    )

    util_module = types.ModuleType("homeassistant.util")
    util_module.__path__ = []  # Make it a package
    monkeypatch.setitem(sys.modules, "homeassistant.util", util_module)

    dt_module = types.ModuleType("homeassistant.util.dt")
    from datetime import datetime

    dt_module.parse_datetime = lambda value: datetime.fromisoformat(value)
    monkeypatch.setitem(sys.modules, "homeassistant.util.dt", dt_module)


def _load_sensor_module(monkeypatch):
    _install_common_homeassistant_stubs(monkeypatch)
    package_name = _install_fake_package(monkeypatch)

    const_module_name = f"{package_name}.const"
    sensor_module_name = f"{package_name}.sensor"
    common_module_name = f"{package_name}.common"
    config_utils_name = f"{package_name}.config_entry_utils"
    register_constants_name = f"{package_name}.register_constants"
    register_types_name = f"{package_name}.register_types"

    _reset_modules(
        const_module_name,
        sensor_module_name,
        common_module_name,
        config_utils_name,
        register_constants_name,
        register_types_name,
    )

    # Create register_types module with SensorRegister class
    register_types_module = types.ModuleType(register_types_name)

    class SensorRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class CalculatedRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    register_types_module.SensorRegister = SensorRegister
    register_types_module.CalculatedRegister = CalculatedRegister
    monkeypatch.setitem(sys.modules, register_types_name, register_types_module)

    # Create const module
    const_module = types.ModuleType(const_module_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.INPUT_DEVICE_INFO = {}
    const_module.CALCULATED_DEVICE_INFO = {}
    const_module.INPUT_REGISTERS = [
        SensorRegister(
            name="Flow rate",
            address=49,
            input_type="input",
            register_name="input_49",
            unit="L/min",
            scale=0.01,
            dtype="uint16",
        ),
        SensorRegister(
            name="Leaving water temperature PHE",
            address=40,
            input_type="input",
            register_name="input_40",
            unit="°C",
            scale=0.01,
            dtype="uint16",
        ),
        SensorRegister(
            name="Return water temperature",
            address=42,
            input_type="input",
            register_name="input_42",
            unit="°C",
            scale=0.01,
            dtype="uint16",
        ),
        SensorRegister(
            name="Heat pump power consumption",
            address=51,
            input_type="input",
            register_name="input_51",
            unit="W",
            scale=10,
            dtype="uint16",
        ),
    ]
    const_module.CALCULATED_SENSORS = [
        CalculatedRegister(
            name="Coefficient of Performance",
            address=0,
            input_type="calculated",
            register_name="cop",
            calc_type="cop",
            unit="CoP",
            translation_key="cop",
        ),
    ]
    monkeypatch.setitem(sys.modules, const_module_name, const_module)

    # Create common module
    common_module = types.ModuleType(common_module_name)

    def get_register_value(data):
        if isinstance(data, dict):
            return data.get("value")
        return None

    def get_register_scale(data):
        if isinstance(data, dict):
            return data.get("scale")
        return None

    def is_entity_available(data, register_name):
        return True

    def is_unavailable_value(val):
        return val in [32765, 32766]

    def to_signed_16bit(val):
        if val > 32767:
            return val - 65536
        return val

    common_module.get_register_value = get_register_value
    common_module.get_register_scale = get_register_scale
    common_module.is_entity_available = is_entity_available
    common_module.is_unavailable_value = is_unavailable_value
    common_module.to_signed_16bit = to_signed_16bit
    monkeypatch.setitem(sys.modules, common_module_name, common_module)

    # Create config_entry_utils module
    config_utils_module = types.ModuleType(config_utils_name)

    def entry_value(entry, key, default=None):
        options = getattr(entry, "options", {}) or {}
        data = getattr(entry, "data", {}) or {}
        return options.get(key, data.get(key, default))

    config_utils_module.entry_value = entry_value
    monkeypatch.setitem(sys.modules, config_utils_name, config_utils_module)

    return importlib.import_module(sensor_module_name)


def test_cop_sensor_with_external_power_sensor(monkeypatch):
    """Test CoP calculation with external power sensor."""
    sensor_module = _load_sensor_module(monkeypatch)

    # Setup: heat_power = 3500W, electric_power = 1000W -> CoP = 3.5
    # Flow = 10 L/min, delta_T = 5K -> heat_power = 10 * 5 * 70 = 3500W
    states = {
        "sensor.external_power": SimpleNamespace(state="1000"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 1000},  # Flow raw = 1000, scaled = 10 L/min
            "input_40": {"value": 4500},  # Temp raw = 4500, scaled = 45°C
            "input_42": {"value": 4000},  # Temp raw = 4000, scaled = 40°C
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 10 * 5 * 70 = 3500W, electric_power = 1000W
    # CoP = 3500 / 1000 = 3.5
    assert sensor.native_value == 3.5


def test_cop_sensor_with_modbus_power_data(monkeypatch):
    """Test CoP calculation with Modbus power data (input_51)."""
    sensor_module = _load_sensor_module(monkeypatch)

    # No external sensor configured - should use input_51
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: None))

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 1000},  # Flow raw = 1000, scaled = 10 L/min
            "input_40": {"value": 4500},  # Temp raw = 4500, scaled = 45°C
            "input_42": {"value": 4000},  # Temp raw = 4000, scaled = 40°C
            "input_51": {"value": 100},  # Power raw = 100, scaled = 1000W
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(data={}, options={}),  # No external sensor
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 10 * 5 * 70 = 3500W, electric_power = 1000W
    # CoP = 3500 / 1000 = 3.5
    assert sensor.native_value == 3.5


def test_cop_sensor_returns_none_when_heat_power_is_zero(monkeypatch):
    """Test that CoP returns None when heat power is zero (pump not running)."""
    sensor_module = _load_sensor_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(state="1000"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 0,
            },  # Flow = 0 L/min
            "input_40": {
                "value": 4500,
            },  # Vorlauf = 45°C
            "input_42": {
                "value": 4500,
            },  # Rücklauf = 45°C, delta_T = 0
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 0, should return None
    assert sensor.native_value is None


def test_cop_sensor_returns_none_when_electric_power_is_zero(monkeypatch):
    """Test that CoP returns None when electric power is zero."""
    sensor_module = _load_sensor_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(state="0"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 1000,
            },  # Flow = 10 L/min
            "input_40": {
                "value": 4500,
            },  # Vorlauf = 45°C
            "input_42": {
                "value": 4000,
            },  # Rücklauf = 40°C
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # electric_power = 0, should return None
    assert sensor.native_value is None


def test_cop_sensor_returns_none_when_external_sensor_unavailable(monkeypatch):
    """Test that CoP returns None when external power sensor is unavailable."""
    sensor_module = _load_sensor_module(monkeypatch)

    # External sensor returns unavailable
    states = {
        "sensor.external_power": SimpleNamespace(state="unavailable"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    # Also no input_51 data available
    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 1000,
            },
            "input_40": {
                "value": 4500,
            },
            "input_42": {
                "value": 4000,
            },
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # electric_power is None, should return None
    assert sensor.native_value is None


def test_cop_sensor_with_unscaled_modbus_data(monkeypatch):
    """Test CoP calculation when Modbus data has no scale stored."""
    sensor_module = _load_sensor_module(monkeypatch)

    hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: None))

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {"value": 1000},  # No scale stored
            "input_40": {"value": 4500},  # No scale stored
            "input_42": {"value": 4000},  # No scale stored
            "input_51": {"value": 100},  # No scale stored, should use default 10
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(data={}, options={}),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # With raw values (no scale in data), the calculation should still work
    # because sensor.py applies scaling from register definition
    # heat_power = (1000 * 0.01) * ((4500 * 0.01) - (4000 * 0.01)) * 70
    #            = 10 * 5 * 70 = 3500W
    # electric_power = 100 * 10 = 1000W
    # CoP = 3500 / 1000 = 3.5
    assert sensor.native_value == 3.5


def test_cop_sensor_rounds_to_two_decimals(monkeypatch):
    """Test that CoP is rounded to 2 decimal places."""
    sensor_module = _load_sensor_module(monkeypatch)

    states = {
        "sensor.external_power": SimpleNamespace(state="1175"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 1000,
            },
            "input_40": {
                "value": 4500,
            },
            "input_42": {
                "value": 4000,
            },
        },
    )

    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={}, options={"electric_power_sensor": "sensor.external_power"}
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 3500W, electric_power = 1175W
    # CoP = 3500 / 1175 = 2.978723... -> should round to 2.98
    assert sensor.native_value == 2.98


def test_cop_sensor_with_legacy_entry_data(monkeypatch):
    """Test CoP calculation when electric_power_sensor is in entry.data (legacy)."""
    sensor_module = _load_sensor_module(monkeypatch)

    states = {
        "sensor.legacy_power": SimpleNamespace(state="500"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id))
    )

    coordinator = SimpleNamespace(
        hass=hass,
        data={
            "input_49": {
                "value": 1000,
            },
            "input_40": {
                "value": 4500,
            },
            "input_42": {
                "value": 4000,
            },
        },
    )

    # Legacy: electric_power_sensor in entry.data, not options
    sensor = sensor_module.CalculatedCoPSensor(
        coordinator=coordinator,
        entry=SimpleNamespace(
            data={"electric_power_sensor": "sensor.legacy_power"},
            options={},
        ),
        unique_id="cop",
        unit="CoP",
        device_class=None,
    )

    # heat_power = 3500W, electric_power = 500W -> CoP = 7.0
    assert sensor.native_value == 7.0
