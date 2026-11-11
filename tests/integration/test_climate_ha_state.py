"""State-machine level rendering of the climate native temperature API.

The regression suite (``test_climate_regressions.py``) proves that the
entities *expose* the HA 2026.11 native_* API and configure
``_attr_native_temperature_unit`` — but that only checks configuration.
This file lets the *real* Home Assistant climate component add the real
entities to the state machine (demo-mode entry, no HA stubs) and checks
the resulting rendered state values: if an implementation used the wrong
API or unit, the attributes would be missing or mis-converted here.

Fahrenheit is deliberately not exercised here: the integration blocks setup
under a Fahrenheit unit system (see ``tests/ha/test_setup_failure_paths.py``),
so every loaded entity always renders Celsius.
"""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.climate.const import HVACAction
from homeassistant.const import CONF_HOST, CONF_PORT, UnitOfTemperature
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import (
    CONF_UNIT_ID,
    DOMAIN,
)
from custom_components.ha_daikin_altherma4_modbus.entities.climate import (
    DaikinDHWThermostat,
    DaikinRoomThermostatMainClimate,
    DaikinThermostatClimate,
)

HOST = "192.0.2.70"


def _demo_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{HOST}:502:1",
        data={CONF_HOST: HOST, CONF_PORT: 502, CONF_UNIT_ID: 1},
        options={"scan_interval": 5, "slow_scan_interval": 30, "demo_mode": True},
    )


# Register payload exactly as the data pipeline stores it: Temp16 readings
# are scaled upstream by ``apply_register_processing`` (raw 2150 -> 21.5),
# and the scale column is retained for downstream special-value detection
# (see test_connection_recovery.py for the raw-to-scaled proof).
DETERMINISTIC_REGISTERS = {
    # Shared operation state
    "holding_3": {"value": 1},  # operation mode -> heating
    "holding_4": {"value": 1},  # space heating/cooling ON
    "input_38": {"value": 1},  # actual op mode -> heating
    "input_31": {"value": 1},  # compressor running
    "discrete_20": {"value": 1},  # main zone running
    "coil_2": {"value": 1},  # main zone enabled
    # Thermostat climate (Leaving water temperature PHE, Temp16)
    "input_40": {"value": 21.5, "scale": 0.01},
    "holding_54": {"value": 2, "scale": 1},  # heating setpoint offset
    "holding_9": {"value": 0},  # quiet mode off
    # Room thermostat Main (input_50 Temp16, holding_76/77 Temp16 setpoints)
    "input_50": {"value": 21.3, "scale": 0.01},
    "holding_76": {"value": 21.5, "scale": 0.01},
    "holding_77": {"value": 23.0, "scale": 0.01},
    "input_84": {"value": 12.0, "scale": 0.01},
    "input_85": {"value": 30.0, "scale": 0.01},
    "input_86": {"value": 12.0, "scale": 0.01},
    "input_87": {"value": 35.0, "scale": 0.01},
    # DHW manual + booster (input_43 Temp16; setpoints holding_10/14 Temp16)
    "input_43": {"value": 50.0, "scale": 0.01},
    "holding_10": {"value": 47.0, "scale": 0.01},
    "holding_14": {"value": 55.0, "scale": 0.01},
    "coil_1": {"value": 1},
    "holding_13": {"value": 1},
    "discrete_19": {"value": 1},
}


async def _setup_with_deterministic_data(hass):
    """Set up a demo entry, then pin the register stream deterministically.

    The demo Modbus mock mixes fixed and random values per read; overlaying
    the core registers on top of the full demo set keeps every lookup
    defined while making the temperature states exactly assertable.
    """
    entry = _demo_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()

    merged = dict(entry.runtime_data.manager.get_all_data())
    merged.update(DETERMINISTIC_REGISTERS)
    entry.runtime_data.manager.get_all_data = MagicMock(return_value=merged)
    entry.runtime_data.coordinator.async_set_updated_data(merged)
    await hass.async_block_till_done()
    return entry


def _entity_id(hass, unique_id):
    """Resolve an entity's object id through the real entity registry."""
    registry = er.async_get(hass)
    matches = [
        entry.entity_id
        for entry in registry.entities.values()
        if entry.unique_id == unique_id and entry.platform == DOMAIN
    ]
    assert len(matches) == 1
    return matches[0]


async def test_ha_renders_thermostat_native_temperatures(
    hass, enable_custom_integrations
):
    """HA reads native_current/target_temperature into the state machine."""
    await _setup_with_deterministic_data(hass)

    state = hass.states.get(_entity_id(hass, f"{DOMAIN}_thermostat_climate"))
    assert state is not None
    # State machine: mode rendered from holding_3/holding_4, not raw ints.
    assert state.state == "heat"

    attrs = state.attributes
    # input_40 stored 21.5 (raw 2150 * 0.01 upstream) renders as 21.5 °C.
    assert attrs["current_temperature"] == pytest.approx(21.5)
    # holding_54 offset (Int16, stored in °C) renders as target 2.0.
    assert attrs["temperature"] == pytest.approx(2.0)
    # Limits/step come from the register catalog through the native API.
    assert attrs["min_temp"] == pytest.approx(-10.0)
    assert attrs["max_temp"] == pytest.approx(10.0)
    assert attrs["target_temp_step"] == pytest.approx(1.0)
    # Compressor on -> real hvac action, not just the mode.
    assert attrs["hvac_action"] == HVACAction.HEATING
    assert attrs["temperature_unit"] == UnitOfTemperature.CELSIUS


async def test_ha_renders_room_thermostat_native_temperatures(
    hass, enable_custom_integrations
):
    """Room thermostat limits and setpoints render through the state machine."""
    await _setup_with_deterministic_data(hass)

    state = hass.states.get(_entity_id(hass, f"{DOMAIN}_room_thermostat_main_climate"))
    assert state.state == "heat"

    attrs = state.attributes
    assert attrs["current_temperature"] == pytest.approx(21.3)
    assert attrs["temperature"] == pytest.approx(21.5)
    # Temp16 limit registers (12..30 °C heating) surface as min/max.
    assert attrs["min_temp"] == pytest.approx(12.0)
    assert attrs["max_temp"] == pytest.approx(30.0)
    assert attrs["target_temp_step"] == pytest.approx(0.5)
    assert attrs["hvac_action"] == HVACAction.HEATING
    assert attrs["temperature_unit"] == UnitOfTemperature.CELSIUS


async def test_ha_renders_dhw_native_temperatures(hass, enable_custom_integrations):
    """Both DHW entities render current/setpoint from their Temp16 registers."""
    await _setup_with_deterministic_data(hass)

    manual = hass.states.get(_entity_id(hass, f"{DOMAIN}_dhw_manual_thermostat"))
    assert manual.state == "heat"
    assert manual.attributes["current_temperature"] == pytest.approx(50.0)
    assert manual.attributes["temperature"] == pytest.approx(47.0)
    assert manual.attributes["hvac_action"] == HVACAction.HEATING
    assert manual.attributes["temperature_unit"] == UnitOfTemperature.CELSIUS

    booster = hass.states.get(_entity_id(hass, f"{DOMAIN}_dhw_booster_thermostat"))
    assert booster.state == "heat"
    assert booster.attributes["current_temperature"] == pytest.approx(50.0)
    assert booster.attributes["temperature"] == pytest.approx(55.0)
    assert booster.attributes["hvac_action"] == HVACAction.HEATING


async def test_entity_public_api_resolves_native_properties(
    hass, enable_custom_integrations
):
    """Real instance-level API: HA's climate component reads native_*, unit via property.

    Complements the class-member regression guard
    (``test_climate_regressions.py::test_climate_uses_native_temperature_api``)
    and the rendered-state check above with the observable property
    behavior: the public ``native_*`` property API returns the register
    values, and HA's deprecated legacy aliases still resolve *through*
    the native API instead of separate attributes.
    """
    entry = await _setup_with_deterministic_data(hass)
    coordinator = entry.runtime_data.coordinator

    def make_entities():
        return [
            (DaikinThermostatClimate(coordinator, entry), 21.5, 2.0),
            (DaikinRoomThermostatMainClimate(coordinator, entry), 21.3, 21.5),
            (DaikinDHWThermostat(coordinator, entry, dhw_type="manual"), 50.0, 47.0),
            (
                DaikinDHWThermostat(coordinator, entry, dhw_type="booster"),
                50.0,
                55.0,
            ),
        ]

    for entity, current, target in make_entities():
        # The public property API is what Home Assistant consumes.
        assert entity.native_temperature_unit == UnitOfTemperature.CELSIUS
        assert entity.native_current_temperature == pytest.approx(current)
        assert entity.native_target_temperature == pytest.approx(target)

        # HA 2026.11 keeps legacy names as deprecated aliases serving the
        # replacement — they must yield the same value via the native API.
        assert entity.current_temperature == pytest.approx(current)
        assert entity.target_temperature == pytest.approx(target)
        assert entity.temperature_unit == UnitOfTemperature.CELSIUS
