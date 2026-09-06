"""Phase-0 compatibility spikes for a future ``modbus-connection`` migration.

These tests document the *behavior of the migration target* (the
``modbus-connection`` library / ``ModbusUnit`` protocol) that the future
integration-facing facade must preserve. They deliberately make no change
to production code — they are executable knowledge for the migration plan:

- **Addressing:** the ``ModbusUnit`` raw API is 0-based (matching pymodbus),
  while this integration defines Daikin registers 1-based (21-87, 1-80, ...).
  The facade must keep the existing ``address - 1`` translation.
- **Special values:** protocol values ``32765 / 32766 / 32767`` pass through
  the unit raw and unfiltered; the integration keeps interpreting them.
- **Errors:** failures are raised as exceptions (``ModbusError`` hierarchy),
  not returned as response objects with ``is_error()``.
- **Writes:** ``write_register``/``write_coil`` map to FC06/FC05 (or FC16/FC15
  for multi-value variants).

The module is skipped when ``modbus-connection`` is not installed so the
normal suite stays green without the migration dependency. It becomes a
permanent regression test once the dependency ships with the integration.
"""

import pytest

pytest.importorskip("modbus_connection")

from modbus_connection.exceptions import IllegalDataAddressError, ModbusError
from modbus_connection.mock import MockModbusConnection

# Daikin register 21 (1-based) equals raw address 20 (0-based).
DAIKIN_ONE_BASED_ADDRESS = 21
RAW_ZERO_BASED_ADDRESS = DAIKIN_ONE_BASED_ADDRESS - 1


def _connected_unit() -> tuple[MockModbusConnection, object]:
    """Return a connected mock connection and unit id 1."""
    connection = MockModbusConnection()
    return connection, connection.for_unit(1)


async def test_unit_read_input_returns_flat_zero_based_list():
    """Spike A1: reads return a flat list addressed 0-based."""
    _, unit = _connected_unit()
    unit.input[RAW_ZERO_BASED_ADDRESS] = 2500  # TEMP16 raw: 25.00 deg C

    values = await unit.read_input_registers(RAW_ZERO_BASED_ADDRESS, 1)

    assert values == [2500]
    # No wrapping response object: raw list, no is_error()/registers indirection.
    assert isinstance(values, list)


async def test_daikin_one_based_address_needs_zero_based_translation():
    """Spike A2: the facade must keep the existing address-1 translation.

    The integration stores 1-based addresses (21-87 in register constants).
    The library reads 0-based, exactly like the current
    ``RealModbusTcpClient`` which already does ``address - 1``.
    """
    _, unit = _connected_unit()
    unit.input[RAW_ZERO_BASED_ADDRESS] = 32767

    # What the facade would issue for Daikin register 21:
    raw = await unit.read_input_registers(DAIKIN_ONE_BASED_ADDRESS - 1, 1)

    assert raw == [32767]
    # Reading at the *untouched* 1-based address would silently read the
    # wrong register, so the translation is a hard contract:
    assert await unit.read_input_registers(DAIKIN_ONE_BASED_ADDRESS, 1) == [0]


async def test_special_values_pass_through_raw():
    """Spike B: 32765/32766/32767 are returned untouched by the unit."""
    _, unit = _connected_unit()
    special = [32765, 32766, 32767]

    for offset, value in enumerate(special):
        unit.input[50 + offset] = value

    values = await unit.read_input_registers(50, 3)

    assert values == special  # nothing filtered / reinterpreted at unit level


async def test_holding_and_bits_are_flat_lists():
    """Spike A3: holding registers (list[int]) and coils (list[bool])."""
    _, unit = _connected_unit()
    unit.holding[5] = 42
    unit.coils[1] = True

    assert await unit.read_holding_registers(5, 1) == [42]
    assert await unit.read_coils(1, 1) == [True]
    assert await unit.read_discrete_inputs(2, 2) == [False, False]


async def test_write_register_maps_to_write_single():
    """Spike C1: single register write stores value and fires FC06 event."""
    _connection, unit = _connected_unit()
    events = []
    unit.on_write(events.append)

    await unit.write_register(10, 42)

    assert unit.holding[10] == 42
    assert events[-1].function_code == 0x06
    assert events[-1].values == [42]


async def test_write_coil_maps_to_write_single_coil():
    """Spike C2: single coil write stores value and fires FC05 event."""
    _connection, unit = _connected_unit()
    events = []
    unit.on_write(events.append)

    await unit.write_coil(2, True)

    assert unit.coils[2] is True
    assert events[-1].function_code == 0x05


async def test_read_failure_raises_exception_instead_of_is_error_response():
    """Spike D: errors are raised, not returned as checkable responses."""
    _connection, unit = _connected_unit()
    unit.fail_read(
        RAW_ZERO_BASED_ADDRESS,
        IllegalDataAddressError("illegal data address"),
        register_type="input",
    )

    with pytest.raises(ModbusError):
        await unit.read_input_registers(RAW_ZERO_BASED_ADDRESS, 1)
