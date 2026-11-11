"""State-machine proof that the offset numbers behave like temperature deltas.

The register-definition test (``tests/unit/test_offset_registers.py``) proves
the metadata: the four weather-dependent LWT offset registers are declared as
``TEMPERATURE_DELTA`` in Celsius. This file lets the *real* Home Assistant
number component add the entities and inspects the rendered state, so the
delta semantics are verified against HA 2026.11 itself instead of being
assumed:

* the entity reports device class ``temperature_delta`` and unit ``°C``,
* the native value stays in Celsius, so the absolute temperature formula is
  never applied (a 2 °C delta must not become 35.6 °F),
* if the user explicitly selects °F as the entity unit, HA applies the delta
  converter (2 °C -> 3.6 °F) for both display and service input
  (36 °F -> 20 °C), never the absolute one.
"""

import pytest
from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers import entity_registry as er
from test_climate_ha_state import _entity_id, _setup_with_deterministic_data

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN

OFFSET_REGISTERS = ("holding_54", "holding_55", "holding_66", "holding_67")


async def test_offset_numbers_expose_delta_semantics(hass, enable_custom_integrations):
    """All offset number entities are °C deltas with the unchanged range."""
    await _setup_with_deterministic_data(hass)

    for register_name in OFFSET_REGISTERS:
        state = hass.states.get(_entity_id(hass, f"{DOMAIN}_{register_name}"))
        assert state is not None, register_name
        assert state.attributes["device_class"] == NumberDeviceClass.TEMPERATURE_DELTA
        assert state.attributes["unit_of_measurement"] == UnitOfTemperature.CELSIUS
        assert (
            state.attributes["min"],
            state.attributes["max"],
            state.attributes["step"],
        ) == (-10, 10, 1)

    # Deterministic register payload: holding_54 holds a 2 °C offset. A delta
    # is rendered as-is; only an explicit unit override converts it.
    offset = hass.states.get(_entity_id(hass, f"{DOMAIN}_holding_54"))
    assert float(offset.state) == pytest.approx(2.0)


async def test_delta_uses_delta_converter_not_absolute_temperature(
    hass, enable_custom_integrations
):
    """°F conversion of an offset is ×1.8 (delta), not ×1.8 + 32 (absolute)."""
    await _setup_with_deterministic_data(hass)

    entity_id = _entity_id(hass, f"{DOMAIN}_holding_54")
    entity = hass.data["entity_components"]["number"].get_entity(entity_id)

    # Number entities do not auto-select a display unit for deltas: the value
    # stays native °C (2 °C), so no absolute 2 °C -> 35.6 °F conversion applies.
    state = hass.states.get(entity_id)
    assert state.attributes["unit_of_measurement"] == UnitOfTemperature.CELSIUS
    assert float(state.state) == pytest.approx(2.0)

    # The user explicitly opts into °F for this delta entity.
    er.async_get(hass).async_update_entity_options(
        entity_id, "number", {"unit_of_measurement": UnitOfTemperature.FAHRENHEIT}
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.attributes["unit_of_measurement"] == UnitOfTemperature.FAHRENHEIT
    # 2 °C delta -> 3.6 °F (×1.8). The absolute conversion would yield 35.6 °F.
    assert float(state.state) == pytest.approx(3.6)
    assert (state.attributes["min"], state.attributes["max"]) == (-18, 18)

    # Service input goes back through the delta converter: 36 °F -> 20 °C,
    # not the absolute 2.2 °C the climate target path would produce.
    assert entity.convert_to_native_value(36.0) == pytest.approx(20.0)
