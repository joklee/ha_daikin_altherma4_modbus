"""Weather-dependent LWT setpoint offsets are temperature differences.

A setpoint *offset* is a delta in °C, not an absolute temperature.
Declaring the offset number registers as ``NumberDeviceClass.TEMPERATURE_DELTA``
makes Home Assistant apply ``TemperatureDeltaConverter`` whenever a unit
conversion is requested (a 2 °C difference -> 3.6 °F) instead of the absolute
temperature converter (2 °C -> 35.6 °F). The register value and its numeric
range stay unchanged; only the semantic class differs.
"""

import pytest
from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfTemperature

from custom_components.ha_daikin_altherma4_modbus.core.register_constants import (
    HOLDING_REGISTERS,
)
from custom_components.ha_daikin_altherma4_modbus.core.register_types import (
    NumberRegister,
)

OFFSET_REGISTERS = ("holding_54", "holding_55", "holding_66", "holding_67")

# Absolute temperature setpoints must not be reclassified as deltas.
ABSOLUTE_SETPOINTS = (
    "holding_16",
    "holding_63",
    "holding_64",
    "holding_76",
    "holding_77",
)


def _register(name: str) -> NumberRegister:
    matches = [reg for reg in HOLDING_REGISTERS if reg.register_name == name]
    assert len(matches) == 1, f"expected exactly one register named {name}"
    register = matches[0]
    assert isinstance(register, NumberRegister)
    return register


@pytest.mark.parametrize("name", OFFSET_REGISTERS)
def test_offset_number_register_is_temperature_delta(name: str) -> None:
    """Every offset register is a °C delta with the original range."""
    register = _register(name)

    assert register.device_class == NumberDeviceClass.TEMPERATURE_DELTA
    assert register.unit == UnitOfTemperature.CELSIUS
    assert (register.min_value, register.max_value, register.step) == (-10, 10, 1)


@pytest.mark.parametrize("name", ABSOLUTE_SETPOINTS)
def test_absolute_setpoint_register_stays_absolute(name: str) -> None:
    """Absolute setpoints keep the absolute temperature class and unit."""
    register = _register(name)

    assert register.device_class != NumberDeviceClass.TEMPERATURE_DELTA
    assert register.unit == UnitOfTemperature.CELSIUS
