"""Focused tests for ``connection_manager.ensure_modbus_connection``.

The former ``test_connection_pool.py`` exercised the integration's own
connection cache, which Phase 3.4 removed: the production code now holds one
client per session (and the HA-backed unit path is shared by the HA ``modbus``
component). These tests pin the remaining ``ensure_modbus_connection``
contract: client creation (real vs. demo), reuse while connected, and lazy
reconnect.
"""

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusConnectionException,
)
from custom_components.ha_daikin_altherma4_modbus.modbus import connection_manager
from custom_components.ha_daikin_altherma4_modbus.modbus.connection_manager import (
    ensure_modbus_connection,
)

HOST = "192.168.1.100"
PORT = 502


class _FakeClient:
    """Recording stand-in for RealModbusTcpClient."""

    def __init__(
        self, host, port=PORT, *, fail_connect=False, stays_disconnected=False
    ):
        self.host = host
        self.port = port
        self.connected = False
        self.connect_calls = 0
        self._fail_connect = fail_connect
        self._stays_disconnected = stays_disconnected

    async def connect(self):
        self.connect_calls += 1
        if self._fail_connect:
            raise ModbusConnectionException(f"connect failed for {self.host}")
        if not self._stays_disconnected:
            self.connected = True


async def test_real_path_creates_and_connects_client(monkeypatch) -> None:
    """A fresh real-path client is created (once) and connected."""
    created = []

    def fake_factory(host, port=PORT):
        client = _FakeClient(host, port)
        created.append(client)
        return client

    monkeypatch.setattr(connection_manager, "RealModbusTcpClient", fake_factory)

    client = await ensure_modbus_connection(None, HOST, PORT, demo_mode=False)

    assert client is created[0]
    assert client.connected is True
    assert client.connect_calls == 1


async def test_demo_path_uses_mock_client(monkeypatch) -> None:
    """Demo mode creates the production MockModbusTcpClient."""
    from custom_components.ha_daikin_altherma4_modbus.modbus.mock_client import (
        MockModbusTcpClient,
    )

    monkeypatch.setattr(connection_manager, "MockModbusTcpClient", MockModbusTcpClient)

    client = await ensure_modbus_connection(None, HOST, PORT, demo_mode=True)

    assert isinstance(client, MockModbusTcpClient)
    assert client.connected is True


async def test_connected_client_is_reused() -> None:
    """An already-connected client is returned without a new connect."""
    client = _FakeClient(HOST, PORT)
    client.connected = True

    result = await ensure_modbus_connection(client, HOST, PORT)

    assert result is client
    assert client.connect_calls == 0


async def test_disconnected_client_is_reconnected() -> None:
    """A dropped client is reconnected in place (same session handle)."""
    client = _FakeClient(HOST, PORT)
    client.connected = False

    result = await ensure_modbus_connection(client, HOST, PORT)

    assert result is client
    assert client.connect_calls == 1
    assert client.connected is True


async def test_connect_failure_propagates() -> None:
    """A failed connect raises ModbusConnectionException (not swallowed)."""
    client = _FakeClient(HOST, PORT, fail_connect=True)

    with pytest.raises(ModbusConnectionException):
        await ensure_modbus_connection(client, HOST, PORT)


async def test_stays_disconnected_raises() -> None:
    """A client that never reaches connected state raises."""
    client = _FakeClient(HOST, PORT, stays_disconnected=True)

    with pytest.raises(ModbusConnectionException):
        await ensure_modbus_connection(client, HOST, PORT)
