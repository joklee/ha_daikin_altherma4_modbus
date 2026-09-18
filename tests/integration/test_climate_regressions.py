import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _restore_module_state():
    """Snapshot & restore ``sys.modules`` for stubbed namespaces.

    The loader below re-imports the climate module while stub modules are
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


def _load_climate_module(monkeypatch):
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.entities.climate"
    const_name = f"{package_name}.core.const"

    _reset_modules(
        module_name,
        const_name,
        "homeassistant.components.climate",
        "homeassistant.components.climate.const",
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

    class EntityCategory:
        DIAGNOSTIC = "diagnostic"

    class UnitOfTemperature:
        CELSIUS = "°C"

    ha_const_module.EntityCategory = EntityCategory
    ha_const_module.UnitOfTemperature = UnitOfTemperature
    monkeypatch.setitem(sys.modules, "homeassistant.const", ha_const_module)

    exceptions_module = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args)
            self.kwargs = kwargs

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
    const_module.SPECIAL_REGISTER_NOT_SUPPORTED = 32767
    const_module.SPECIAL_REGISTER_NOT_AVAILABLE = (32766,)
    const_module.SPECIAL_REGISTER_WAITING = 32765
    monkeypatch.setitem(sys.modules, const_name, const_module)

    module = importlib.import_module(module_name)
    # Attach HomeAssistantError to module so tests can access it
    module.HomeAssistantError = exceptions_module.HomeAssistantError
    return module


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


def _make_dhw_thermostat(module, dhw_type="manual", **overrides):
    data = {
        "coil_1": {"value": 1},
        "discrete_19": {"value": 1},
        "input_43": {"value": 50.0},
        "holding_80": {"value": 45, "scale": 1},
        "holding_13": {"value": 1},
        "holding_81": {"value": 45, "scale": 1},
    }
    data.update(overrides)
    coordinator = SimpleNamespace(
        data=data,
        data_manager=SimpleNamespace(
            write_holding_register=AsyncMock(),
            write_coil_register=AsyncMock(),
        ),
    )
    return module.DaikinDHWThermostat(
        coordinator, entry=SimpleNamespace(), dhw_type=dhw_type
    )


def test_thermostat_current_temperature_scaled_and_unscaled(monkeypatch):
    """Current temperature honors pre-scaled values and scales raw ones."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    assert thermostat.current_temperature == pytest.approx(21.5)

    thermostat.coordinator.data["input_37"] = {"value": 2150}
    assert thermostat.current_temperature == pytest.approx(2150.0)


def test_thermostat_target_temperature_heating_and_cooling(monkeypatch):
    """Target temperature follows the mode-selected offset register."""
    module = _load_climate_module(monkeypatch)
    assert _make_thermostat(module).target_temperature == pytest.approx(0.0)

    cool = _make_thermostat(module, op_mode_raw=2)
    cool.coordinator.data["holding_6"] = {"value": 200}
    assert cool.target_temperature == pytest.approx(200.0)


def test_thermostat_fan_and_hvac_modes(monkeypatch):
    """Fan and hvac modes map raw values to HA modes."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    assert thermostat.fan_mode == "OFF"
    assert thermostat.fan_modes == ["OFF", "Auto", "Manual"]
    assert thermostat.hvac_mode == "auto"

    thermostat.coordinator.data["holding_3"] = {"value": 1}
    assert thermostat.hvac_mode == "heat"
    thermostat.coordinator.data["holding_3"] = {"value": 2}
    assert thermostat.hvac_mode == "cool"
    thermostat.coordinator.data["holding_9"] = {"value": 1}
    assert thermostat.fan_mode == "Auto"


def test_thermostat_hvac_action(monkeypatch):
    """Running action follows compressor state and current mode."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    assert thermostat.hvac_action == "idle"

    thermostat.coordinator.data["discrete_11"] = {"value": 1}
    thermostat.coordinator.data["holding_3"] = {"value": 1}
    assert thermostat.hvac_action == "heating"
    thermostat.coordinator.data["holding_3"] = {"value": 2}
    assert thermostat.hvac_action == "cooling"


def test_thermostat_step_min_max_from_catalog_and_fallback(monkeypatch):
    """Step/min/max come from the register catalog, with safe fallbacks."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    # Real catalog: holding_7 (heating offset) step 1, range 12..35.
    assert thermostat.target_temperature_step == pytest.approx(1.0)
    assert thermostat.min_temp == pytest.approx(12)
    assert thermostat.max_temp == pytest.approx(35)

    monkeypatch.setattr(module, "HOLDING_REGISTERS", [])
    assert thermostat.target_temperature_step == pytest.approx(0.1)
    assert thermostat.min_temp == pytest.approx(-5)
    assert thermostat.max_temp == pytest.approx(5)


@pytest.mark.asyncio
async def test_thermostat_set_temperature_heating_and_cooling(monkeypatch):
    """Setpoint writes go to the mode-selected offset register."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    await thermostat.async_set_temperature(temperature=20.0)
    thermostat.coordinator.data_manager.write_holding_register.assert_awaited_with(
        "holding_7", 20
    )

    cool = _make_thermostat(module, op_mode_raw=2)
    await cool.async_set_temperature(temperature=25.0)
    cool.coordinator.data_manager.write_holding_register.assert_awaited_with(
        "holding_6", 25
    )


@pytest.mark.asyncio
async def test_thermostat_set_temperature_clamps_to_limits(monkeypatch):
    """Out-of-range setpoints are clamped to the catalog limits."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    await thermostat.async_set_temperature(temperature=2.0)
    thermostat.coordinator.data_manager.write_holding_register.assert_awaited_with(
        "holding_7", 12
    )


@pytest.mark.asyncio
async def test_thermostat_set_temperature_without_value_is_noop(monkeypatch):
    """A missing temperature parameter only warns."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    await thermostat.async_set_temperature()
    thermostat.coordinator.data_manager.write_holding_register.assert_not_awaited()


@pytest.mark.asyncio
async def test_thermostat_extra_attributes_and_power_switch(monkeypatch):
    """Attributes expose quiet mode/offset/setpoint; on/off map to AUTO."""
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    attrs = thermostat.extra_state_attributes
    assert attrs["quiet_mode"] == "Off"
    assert attrs["offset"] == pytest.approx(0.0)
    assert attrs["calculated_setpoint"] == pytest.approx(21.5)
    assert attrs["register_config"]["address"] == "holding_7"

    await thermostat.async_turn_on()
    await thermostat.async_turn_off()
    assert thermostat.coordinator.data_manager.write_holding_register.await_count == 2


@pytest.mark.asyncio
async def test_dhw_thermostat_modes_and_temps(monkeypatch):
    """DHW thermostat reports mode, action and temperatures."""
    module = _load_climate_module(monkeypatch)
    dhw = _make_dhw_thermostat(module)
    assert dhw.hvac_mode == "heat"
    assert dhw.hvac_action == "heating"
    assert dhw.current_temperature == pytest.approx(50.0)
    assert dhw.target_temperature == pytest.approx(45)
    assert dhw.available is True

    dhw.coordinator.data["coil_1"] = {"value": 0}
    assert dhw.hvac_mode == "off"
    assert dhw.hvac_action == "off"
    assert dhw.available is True

    del dhw.coordinator.data["coil_1"]
    assert dhw.available is False


@pytest.mark.asyncio
async def test_dhw_thermostat_idle_when_not_running(monkeypatch):
    """Heat mode without a running flag reports idle."""
    module = _load_climate_module(monkeypatch)
    dhw = _make_dhw_thermostat(module, discrete_19={"value": 0})
    assert dhw.hvac_mode == "heat"
    assert dhw.hvac_action == "idle"


@pytest.mark.asyncio
async def test_dhw_thermostat_writes(monkeypatch):
    """Mode and setpoint writes reach the mode-selected registers."""
    module = _load_climate_module(monkeypatch)
    dhw = _make_dhw_thermostat(module)
    await dhw.async_set_hvac_mode("heat")
    dhw.coordinator.data_manager.write_coil_register.assert_awaited_with("coil_1", 1)
    await dhw.async_set_hvac_mode("off")
    dhw.coordinator.data_manager.write_coil_register.assert_awaited_with("coil_1", 0)

    await dhw.async_set_temperature(temperature=50.0)
    dhw.coordinator.data_manager.write_holding_register.assert_awaited_with(
        "holding_80", 50
    )
    dhw.coordinator.data_manager.write_holding_register.reset_mock()
    await dhw.async_set_temperature()
    dhw.coordinator.data_manager.write_holding_register.assert_not_awaited()

    await dhw.async_turn_on()
    await dhw.async_turn_off()


@pytest.mark.asyncio
async def test_dhw_booster_thermostat(monkeypatch):
    """Booster variant wires holding registers for mode and setpoint."""
    module = _load_climate_module(monkeypatch)
    booster = _make_dhw_thermostat(module, dhw_type="booster")
    assert booster.hvac_mode == "heat"
    assert booster.available is True
    await booster.async_set_hvac_mode("heat")
    booster.coordinator.data_manager.write_holding_register.assert_awaited_with(
        "holding_13", 1
    )
    await booster.async_set_temperature(temperature=50.0)
    booster.coordinator.data_manager.write_holding_register.assert_awaited_with(
        "holding_81", 50
    )


def test_thermostat_available_requires_core_registers(monkeypatch):
    """Availability tracks the operation-mode and current-temp registers.

    Silver ``entity-unavailable``: the stub maps REGISTER_CURRENT_TEMP to
    ``input_37``, which the fixture seeds, so the thermostat starts
    available and goes unavailable when a core register drops out or
    reports a special (unsupported) value.
    """
    module = _load_climate_module(monkeypatch)
    thermostat = _make_thermostat(module)
    assert thermostat.available is True

    del thermostat.coordinator.data["holding_3"]
    assert thermostat.available is False

    thermostat.coordinator.data["holding_3"] = {"value": 0}
    thermostat.coordinator.data["input_37"] = {"value": 32767}
    assert thermostat.available is False


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
