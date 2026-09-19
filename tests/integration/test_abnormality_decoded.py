"""Tests for the decoded abnormality sensor (issue #79).

The sensor shows e.g. "7H-19" while input_21 signals fault/warning and
unknown otherwise; the meaning rides along as an attribute.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.common.helpers import (
    get_register_value,
)
from custom_components.ha_daikin_altherma4_modbus.core.const import (
    CONF_UNIT_ID,
    DOMAIN,
)
from custom_components.ha_daikin_altherma4_modbus.entities.sensor import (
    AbnormalityDecodedSensor,
)
from tests.fakes.modbus import FakeModbusResponse


def _make_sensor(data):
    coordinator = SimpleNamespace(data=data)
    entry = SimpleNamespace(entry_id="test")
    return AbnormalityDecodedSensor(
        coordinator,
        entry,
        unique_id="ha_daikin_altherma4_modbus_abnormality_decoded",
        translation_key="abnormality_decoded",
    )


def _data(status, code=14152, sub=19):
    return {
        "input_21": {"value": status},
        "input_22": {"value": code},
        "input_23": {"value": sub},
    }


def test_decoded_value_and_attributes_on_fault():
    sensor = _make_sensor(_data(status=1))
    assert sensor.native_value == "7H-19"
    assert sensor.available is True
    assert (
        sensor.extra_state_attributes["description"]
        == "Water flow requirement problem at tank heat-up request"
    )
    assert sensor.extra_state_attributes["code_raw"] == 14152
    assert sensor.extra_state_attributes["sub_code_raw"] == 19


def test_decoded_value_on_warning():
    sensor = _make_sensor(_data(status=2))
    assert sensor.native_value == "7H-19"


def test_unknown_without_active_fault():
    sensor = _make_sensor(_data(status=0))
    assert sensor.native_value is None
    assert sensor.extra_state_attributes["description"] is None


def test_unknown_code_still_shows_raw_shape():
    """An unlisted code decodes structurally; description stays empty."""
    sensor = _make_sensor(_data(status=1, code=0x5A5A, sub=3))
    assert sensor.native_value == "ZZ-3"
    assert sensor.extra_state_attributes["description"] is None


def test_missing_sub_code_shows_main_code_only():
    sensor = _make_sensor(
        {
            "input_21": {"value": 1},
            "input_22": {"value": 14152},
        }
    )
    assert sensor.native_value == "7H"


def test_undecodable_code_is_unknown():
    sensor = _make_sensor(_data(status=1, code=32767, sub=19))
    assert sensor.native_value is None


def test_missing_data_is_unknown_but_available_with_any_data():
    sensor = _make_sensor({})
    assert sensor.native_value is None
    assert sensor.available is False
    assert _make_sensor({"input_21": {"value": 0}}).available is True


def _demo_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.0.2.90:502:1",
        data={CONF_HOST: "192.0.2.90", CONF_PORT: 502, CONF_UNIT_ID: 1},
        options={"scan_interval": 5, "slow_scan_interval": 30, "demo_mode": True},
    )


def _abnormality_entity_id(hass):
    registry = er.async_get(hass)
    matches = [
        entry.entity_id
        for entry in registry.entities.values()
        if entry.unique_id == "abnormality_decoded" and entry.platform == DOMAIN
    ]
    assert len(matches) == 1
    return matches[0]


def _fault_response():
    """Input block with an active 7H-19 fault (1-based array)."""
    regs = [32767] * 88
    regs[21] = 1
    regs[22] = 14152
    regs[23] = 19
    return FakeModbusResponse(regs, 21, 67)


@pytest.mark.asyncio
async def test_ha_renders_no_fault_as_unknown(hass, enable_custom_integrations):
    """Home Assistant shows "unknown" (not unavailable) with no fault.

    native_value None + available True must render as state "unknown" -
    the consciously chosen representation for "no active fault".
    """
    entry = _demo_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()

    entity_id = _abnormality_entity_id(hass)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"


@pytest.mark.asyncio
async def test_ha_renders_active_fault_as_code(hass, enable_custom_integrations):
    """An injected 7H-19 fault renders as the decoded code string."""
    entry = _demo_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()

    entity_id = _abnormality_entity_id(hass)
    assert hass.states.get(entity_id).state == "unknown"

    coordinator = entry.runtime_data.normal_coordinator
    coordinator.data_manager.client.read_input_registers = AsyncMock(
        return_value=_fault_response()
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "7H-19"


def test_production_mapping_yields_raw_integer():
    """Review #79: coordinator data holds raw 14152 (int), not "7H".

    The TEXT16 str() conversion happens only in the display entity;
    the mapping stores the raw integer, which the decoder consumes.
    """
    from custom_components.ha_daikin_altherma4_modbus.core.mapping_transform import (
        ModbusMappingTransform,
    )
    from custom_components.ha_daikin_altherma4_modbus.core.register_constants import (
        INPUT_REGISTERS,
    )

    raw_block = [0] * 67
    raw_block[0] = 1  # input_21: fault
    raw_block[1] = 14152  # input_22: raw abnormality code
    raw_block[2] = 19  # input_23: sub code

    mapping = ModbusMappingTransform()
    data = mapping.process_input_register_block(raw_block, INPUT_REGISTERS, 21, 87, 21)

    stored = get_register_value(data["input_22"])
    assert stored == 14152
    assert isinstance(stored, int)
    assert _make_sensor(data).native_value == "7H-19"
