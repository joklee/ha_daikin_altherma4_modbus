"""Unit tests for the Phase-2 ``ModbusConnectionClient`` facade.

The facade adapts ``modbus_connection.ModbusUnit`` to the integration's
:class:`ModbusClientInterface`: it translates 1-based Daikin addresses to the
0-based raw API, passes special values through untouched, maps the
``ModbusError`` hierarchy onto the integration's exceptions, and maps
writes to FC06/FC05.

Skipped when ``modbus-connection`` is not installed so the normal suite stays
green without the migration dependency.
"""

import pytest

pytest.importorskip("modbus_connection")

from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection

from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusConnectionException,
    ModbusInvalidAddressException,
    ModbusReadException,
    ModbusTimeoutException,
    ModbusWriteException,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.modbus_connection_client import (
    ModbusConnectionClient,
)

# Daikin register 21 (1-based) equals raw address 20 (0-based).
DAIKIN_ONE_BASED_ADDRESS = 21
RAW_ZERO_BASED_ADDRESS = DAIKIN_ONE_BASED_ADDRESS - 1


def _make_client() -> tuple[MockModbusConnection, ModbusConnectionClient]:
    """Return a mock connection and a facade bound to unit id 1."""
    connection = MockModbusConnection()
    client = ModbusConnectionClient(connection, unit_id=1)
    return connection, client


# --- Address translation (spike A2 contract) ---------------------------------


async def test_read_input_registers_translates_to_zero_based() -> None:
    connection, client = _make_client()
    connection.for_unit(1).input[RAW_ZERO_BASED_ADDRESS] = 2500  # TEMP16 25.00°C

    values = await client.read_input_registers(DAIKIN_ONE_BASED_ADDRESS, 1)

    assert values == [2500]


async def test_read_holding_registers_translates_to_zero_based() -> None:
    connection, client = _make_client()
    connection.for_unit(1).holding[RAW_ZERO_BASED_ADDRESS] = 42

    values = await client.read_holding_registers(DAIKIN_ONE_BASED_ADDRESS, 1)

    assert values == [42]


# --- Flat-list return values ------------------------------------------------


async def test_reads_return_flat_lists() -> None:
    connection, client = _make_client()
    unit = connection.for_unit(1)
    unit.holding[5] = 42
    unit.coils[1] = True

    assert await client.read_holding_registers(6, 1) == [42]
    assert isinstance(await client.read_holding_registers(6, 1), list)
    assert await client.read_coils(2, 1) == [True]
    assert await client.read_discrete_inputs(3, 2) == [False, False]


# --- Special value passthrough ----------------------------------------------


async def test_special_values_pass_through_raw() -> None:
    connection, client = _make_client()
    special = [32765, 32766, 32767]
    for offset, value in enumerate(special):
        connection.for_unit(1).input[50 + offset] = value

    values = await client.read_input_registers(51, 3)

    assert values == special


# --- Error mapping -----------------------------------------------------------


async def test_illegal_address_read_maps_to_invalid_address() -> None:
    connection, client = _make_client()
    connection.for_unit(1).fail_read(
        RAW_ZERO_BASED_ADDRESS,
        IllegalDataAddressError("illegal data address"),
        register_type="input",
    )

    with pytest.raises(ModbusInvalidAddressException):
        await client.read_input_registers(DAIKIN_ONE_BASED_ADDRESS, 1)


async def test_timeout_read_maps_to_timeout_exception() -> None:
    connection, client = _make_client()
    connection.for_unit(1).fail_read(
        RAW_ZERO_BASED_ADDRESS,
        ModbusTimeoutError("timed out"),
        register_type="input",
    )

    with pytest.raises(ModbusTimeoutException):
        await client.read_input_registers(DAIKIN_ONE_BASED_ADDRESS, 1)


async def test_connection_error_read_maps_to_connection_exception() -> None:
    connection, client = _make_client()
    connection.for_unit(1).fail_read(
        RAW_ZERO_BASED_ADDRESS,
        ModbusConnectionError("connection lost"),
        register_type="input",
    )

    with pytest.raises(ModbusConnectionException):
        await client.read_input_registers(DAIKIN_ONE_BASED_ADDRESS, 1)


async def test_generic_modbus_error_read_maps_to_read_exception() -> None:
    connection, client = _make_client()
    connection.for_unit(1).fail_read(
        RAW_ZERO_BASED_ADDRESS,
        ModbusError("generic failure"),
        register_type="input",
    )

    with pytest.raises(ModbusReadException):
        await client.read_input_registers(DAIKIN_ONE_BASED_ADDRESS, 1)


async def test_modbus_error_write_maps_to_write_exception() -> None:
    connection, client = _make_client()
    connection.for_unit(1).fail_write(
        RAW_ZERO_BASED_ADDRESS,
        ModbusError("write rejected"),
    )

    with pytest.raises(ModbusWriteException):
        await client.write_holding_register(DAIKIN_ONE_BASED_ADDRESS, 42)


# --- Write mapping (FC06 / FC05) ---------------------------------------------


async def test_write_holding_register_maps_to_write_register() -> None:
    connection, client = _make_client()
    unit = connection.for_unit(1)
    events = []
    unit.on_write(events.append)

    await client.write_holding_register(11, 42)

    # Daikin 1-based 11 -> raw 10; value unchanged.
    assert unit.holding[10] == 42
    assert events[-1].function_code == 0x06
    assert events[-1].values == [42]


async def test_write_coil_register_maps_to_write_coil() -> None:
    connection, client = _make_client()
    unit = connection.for_unit(1)
    events = []
    unit.on_write(events.append)

    await client.write_coil_register(3, True)

    # Daikin 1-based 3 -> raw 2.
    assert unit.coils[2] is True
    assert events[-1].function_code == 0x05


async def test_connection_error_coil_write_maps_to_connection_exception() -> None:
    connection, client = _make_client()
    connection.for_unit(1).fail_write(
        2,
        ModbusConnectionError("link down"),
        register_type="coil",
    )

    with pytest.raises(ModbusConnectionException):
        await client.write_coil_register(3, True)


async def test_owned_connection_connect_and_disconnect() -> None:
    connection, client = _make_client()
    assert client.connected is False

    await client.connect()
    assert client.connected is True
    assert connection.connected is True

    await client.disconnect()
    assert client.connected is False
    assert connection.connected is False
