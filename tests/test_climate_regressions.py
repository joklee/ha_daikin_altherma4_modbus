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


def _load_climate_module(monkeypatch):
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.climate"
    const_name = f"{package_name}.const"

    _reset_modules(
        module_name,
        const_name,
        "homeassistant.components.climate",
        "homeassistant.components.climate.const",
        "homeassistant.const",
        "homeassistant.exceptions",
        "homeassistant.helpers.update_coordinator",
    )

    climate_component_module = types.ModuleType("homeassistant.components.climate")
    climate_component_module.ClimateEntity = object
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.climate", climate_component_module
    )

    climate_const_module = types.ModuleType("homeassistant.components.climate.const")

    class HVACMode:
        OFF = "off"
        HEAT = "heat"
        COOL = "cool"
        AUTO = "auto"

    class HVACAction:
        OFF = "off"
        HEATING = "heating"
        COOLING = "cooling"
        IDLE = "idle"

    class ClimateEntityFeature:
        TARGET_TEMPERATURE = 1
        FAN_MODE = 2

    climate_const_module.HVACMode = HVACMode
    climate_const_module.HVACAction = HVACAction
    climate_const_module.ClimateEntityFeature = ClimateEntityFeature
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.climate.const", climate_const_module
    )

    ha_const_module = types.ModuleType("homeassistant.const")

    class UnitOfTemperature:
        CELSIUS = "C"

    ha_const_module.UnitOfTemperature = UnitOfTemperature
    monkeypatch.setitem(sys.modules, "homeassistant.const", ha_const_module)

    exceptions_module = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions_module.HomeAssistantError = HomeAssistantError
    monkeypatch.setitem(sys.modules, "homeassistant.exceptions", exceptions_module)

    coordinator_module = types.ModuleType("homeassistant.helpers.update_coordinator")

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    coordinator_module.CoordinatorEntity = CoordinatorEntity
    monkeypatch.setitem(
        sys.modules, "homeassistant.helpers.update_coordinator", coordinator_module
    )

    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.CALCULATED_DEVICE_INFO = {"identifiers": {("x", "y")}}
    const_module.HOLDING_REGISTERS = []
    const_module.INPUT_REGISTERS = []
    const_module.REGISTER_OPERATION_MODE = "holding_3"
    const_module.HVAC_COOL = 2
    const_module.REGISTER_OFFSET_COOLING = "holding_6"
    const_module.REGISTER_OFFSET_HEATING = "holding_7"
    const_module.REGISTER_CURRENT_TEMP = "input_37"
    const_module.DHW_OFF = 0
    const_module.DHW_ON = 1
    const_module.REGISTER_DHW_SETPOINT = "holding_80"
    const_module.REGISTER_DHW_RUNNING = "discrete_19"
    const_module.REGISTER_DHW_HVAC_MODE = "coil_1"
    const_module.REGISTER_DHW_BOOSTER_SETPOINT = "holding_81"
    const_module.REGISTER_DHW_BOOSTER_TEMP = "input_43"
    const_module.REGISTER_DHW_BOOSTER_RUNNING = "discrete_19"
    const_module.REGISTER_DHW_BOOSTER_HVAC_MODE = "holding_13"
    const_module.REGISTER_QUIET_MODE = "holding_9"
    const_module.FAN_MANUAL = "Manual"
    const_module.HVAC_HEAT = 1
    const_module.HVAC_OFF = 0
    const_module.REGISTER_COMPRESSOR = "discrete_11"
    const_module.FAN_AUTO = "Auto"
    const_module.FAN_OFF = "OFF"
    const_module.REGISTER_DHW_TEMP = "input_43"
    monkeypatch.setitem(sys.modules, const_name, const_module)

    return importlib.import_module(module_name)


def _make_thermostat(module, quiet_raw=0, op_mode_raw=0):
    coordinator = SimpleNamespace(
        data={
            "holding_9": {"value": quiet_raw},
            "holding_3": {"value": op_mode_raw},
            "input_37": {"value": 21.5, "scale": 1},
            "holding_7": {"value": 0, "scale": 1, "min_value": -5, "max_value": 5},
            "discrete_11": {"value": 0},
        },
        data_manager=SimpleNamespace(write_holding_register=AsyncMock()),
    )
    return module.DaikinThermostatClimate(coordinator, entry=SimpleNamespace())


@pytest.mark.asyncio
async def test_fan_mode_read_write_mapping(monkeypatch):
    module = _load_climate_module(monkeypatch)

    thermostat = _make_thermostat(module, quiet_raw=0)
    assert thermostat.fan_mode == module.FAN_OFF
    await thermostat.async_set_fan_mode(module.FAN_OFF)
    thermostat.coordinator.data_manager.write_holding_register.assert_awaited_with(
        module.REGISTER_QUIET_MODE, 0
    )

    thermostat = _make_thermostat(module, quiet_raw=1)
    assert thermostat.fan_mode == module.FAN_AUTO
    await thermostat.async_set_fan_mode(module.FAN_AUTO)
    thermostat.coordinator.data_manager.write_holding_register.assert_awaited_with(
        module.REGISTER_QUIET_MODE, 1
    )

    thermostat = _make_thermostat(module, quiet_raw=2)
    assert thermostat.fan_mode == module.FAN_MANUAL
    await thermostat.async_set_fan_mode(module.FAN_MANUAL)
    thermostat.coordinator.data_manager.write_holding_register.assert_awaited_with(
        module.REGISTER_QUIET_MODE, 2
    )


@pytest.mark.asyncio
async def test_hvac_off_is_coerced_to_auto_register_value(monkeypatch):
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module, op_mode_raw=0)

    assert thermostat.hvac_mode == module.HVACMode.AUTO
    assert module.HVACMode.OFF not in thermostat._attr_hvac_modes

    await thermostat.async_set_hvac_mode(module.HVACMode.OFF)
    thermostat.coordinator.data_manager.write_holding_register.assert_awaited_with(
        module.REGISTER_OPERATION_MODE, 0
    )

    thermostat.coordinator.data_manager.write_holding_register.reset_mock()
    await thermostat.async_turn_off()
    thermostat.coordinator.data_manager.write_holding_register.assert_awaited_with(
        module.REGISTER_OPERATION_MODE, 0
    )


@pytest.mark.asyncio
async def test_hvac_mode_raises_home_assistant_error_on_failed_write(monkeypatch):
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module, op_mode_raw=0)
    # Mock write_holding_register to raise a connection error (simulating device unreachable)
    thermostat.coordinator.data_manager.write_holding_register = AsyncMock(
        side_effect=ConnectionError("Device unreachable")
    )

    with pytest.raises(module.HomeAssistantError):
        await thermostat.async_set_hvac_mode(module.HVACMode.HEAT)


@pytest.mark.asyncio
async def test_fan_mode_raises_home_assistant_error_on_exception(monkeypatch):
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module, quiet_raw=1)
    thermostat.coordinator.data_manager.write_holding_register = AsyncMock(
        side_effect=RuntimeError("write boom")
    )

    with pytest.raises(module.HomeAssistantError):
        await thermostat.async_set_fan_mode(module.FAN_AUTO)
