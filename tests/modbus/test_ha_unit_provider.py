"""Tests for the Phase 3.2 HA-backed unit provider.

``async_get_ha_unit`` wraps the unit that HA's ``modbus`` component hands out
(via ``async_get_unit``) in a :class:`ModbusConnectionClient`, so reads go
through the facade's 1-based to 0-based address translation.

Skipped when ``modbus-connection`` is not installed.
"""

import pytest

pytest.importorskip("modbus_connection")

from modbus_connection.mock import MockModbusConnection

from custom_components.ha_daikin_altherma4_modbus.modbus import (
    connection_manager,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.connection_manager import (
    async_get_ha_unit,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.modbus_connection_client import (
    ModbusConnectionClient,
)

HOST = "192.168.1.100"
PORT = 502
UNIT_ID = 1


def _fake_async_get_unit(hass, entry, params, unit_id):
    """Stand-in for HA's ``async_get_unit`` returning a mock unit."""
    connection = MockModbusConnection()
    return connection.for_unit(unit_id)


async def test_async_get_ha_unit_calls_async_get_unit_with_expected_args(
    monkeypatch,
) -> None:
    """The provider delegates to HA's ``async_get_unit`` with (host, port)."""
    captured = {}

    def fake_get_unit(hass, entry, params, unit_id):
        captured["hass"] = hass
        captured["entry"] = entry
        captured["params"] = params
        captured["unit_id"] = unit_id
        return _fake_async_get_unit(hass, entry, params, unit_id)

    class FakeTcpParams:
        def __init__(self, *, host, port):
            self.host = host
            self.port = port

    monkeypatch.setattr(connection_manager, "async_get_unit", fake_get_unit)
    monkeypatch.setattr(connection_manager, "ModbusTcpParams", FakeTcpParams)

    hass = object()
    entry = object()
    client = await async_get_ha_unit(hass, entry, HOST, PORT, UNIT_ID)

    assert captured["hass"] is hass
    assert captured["entry"] is entry
    assert captured["params"].host == HOST
    assert captured["params"].port == PORT
    assert captured["unit_id"] == UNIT_ID
    assert isinstance(client, ModbusConnectionClient)


async def test_async_get_ha_unit_wraps_unit_and_translates_address(
    monkeypatch,
) -> None:
    """The returned facade reads through the shared unit, 1-based to 0-based."""
    connection = MockModbusConnection()

    def fake_get_unit(hass, entry, params, unit_id):
        return connection.for_unit(unit_id)

    class FakeTcpParams:
        def __init__(self, *, host, port):
            self.host = host
            self.port = port

    monkeypatch.setattr(connection_manager, "async_get_unit", fake_get_unit)
    monkeypatch.setattr(connection_manager, "ModbusTcpParams", FakeTcpParams)

    connection.for_unit(UNIT_ID).input[20] = 2500  # Daikin register 21 -> raw 20

    client = await async_get_ha_unit(object(), object(), HOST, PORT, UNIT_ID)

    # Daikin 1-based address 21 is read at raw 0-based address 20.
    assert await client.read_input_registers(21, 1) == [2500]


async def test_modbus_connection_client_constructed_from_unit_directly() -> None:
    """A facade built directly from a unit works without a connection."""
    connection = MockModbusConnection()
    unit = connection.for_unit(UNIT_ID)
    unit.holding[5] = 42

    client = ModbusConnectionClient(unit=unit)

    # No owned connection: connect is a no-op, connected reports via the unit.
    assert client.connected is unit.connected
    await client.connect()  # must not raise without a connection
    await client.disconnect()  # must not raise without a connection

    assert await client.read_holding_registers(6, 1) == [42]
