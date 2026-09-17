"""Tests for the transport session on the HA-backed default path.

``ModbusTransportSession`` obtains its client via the HA-backed provider when
``hass``/``entry`` are set (lazy, no I/O), connects the demo mock in demo
mode, and raises ``ModbusConnectionException`` for real mode without
``hass``/``entry`` (no ``pymodbus``-direct fallback since the Phase 5
cutover). On the HA path ``reconnect_with_new_client`` must not recreate the
shared connection — it returns the same shared unit.

Skipped when ``modbus-connection`` is not installed.
"""

import pytest

pytest.importorskip("modbus_connection")

from modbus_connection.mock import MockModbusConnection

from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusConnectionException,
)
from custom_components.ha_daikin_altherma4_modbus.modbus import transport_session
from custom_components.ha_daikin_altherma4_modbus.modbus.connection_manager import (
    async_get_ha_unit,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.mock_client import (
    MockModbusTcpClient,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.modbus_connection_client import (
    ModbusConnectionClient,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.transport_session import (
    ModbusTransportSession,
)

HOST = "192.168.1.100"
PORT = 502
UNIT_ID = 1


def _install_fake_provider(monkeypatch, connection=None):
    """Install a fake HA-backed provider returning the real facade."""
    connection = connection or MockModbusConnection()
    calls = {"count": 0}

    async def fake_get_ha_unit(hass, entry, host, port, unit_id):
        calls["count"] += 1
        return ModbusConnectionClient(unit=connection.for_unit(unit_id))

    monkeypatch.setattr(transport_session, "async_get_ha_unit", fake_get_ha_unit)
    return connection, calls


async def test_ensure_connection_uses_ha_backed_path_when_hass_entry_set(
    monkeypatch,
) -> None:
    """With hass/entry set, the session obtains a client lazily (no connect)."""
    connection = MockModbusConnection()
    _, calls = _install_fake_provider(monkeypatch, connection)

    session = ModbusTransportSession(
        HOST, PORT, hass=object(), entry=object(), unit_id=UNIT_ID
    )

    client = await session.ensure_connection()

    assert calls["count"] == 1
    assert client is not None
    # Lazy: no connect was triggered on the shared connection.
    assert connection.connected is False


async def test_reconnect_with_new_client_keeps_shared_unit(monkeypatch) -> None:
    """Reconnect returns the same shared unit, not a fresh connection."""
    connection = MockModbusConnection()
    _, calls = _install_fake_provider(monkeypatch, connection)

    session = ModbusTransportSession(
        HOST, PORT, hass=object(), entry=object(), unit_id=UNIT_ID
    )

    first = await session.ensure_connection()
    second = await session.reconnect_with_new_client()

    # Both handles wrap the same shared unit (same underlying connection).
    assert first is not None and second is not None
    assert first._unit is second._unit
    assert calls["count"] == 2  # refreshed handle, same shared unit


async def test_demo_mode_connects_mock_without_ha_provider(monkeypatch) -> None:
    """Demo mode connects the mock even when hass/entry are present."""
    ha_called = {"value": False}

    async def fake_get_ha_unit(hass, entry, host, port, unit_id):
        ha_called["value"] = True
        raise AssertionError("HA provider must not be used in demo mode")

    monkeypatch.setattr(transport_session, "async_get_ha_unit", fake_get_ha_unit)

    session = ModbusTransportSession(
        HOST, PORT, demo_mode=True, hass=object(), entry=object(), unit_id=UNIT_ID
    )

    client = await session.ensure_connection()

    assert ha_called["value"] is False
    assert isinstance(client, MockModbusTcpClient)
    assert client.connected is True


async def test_demo_reconnect_returns_fresh_mock() -> None:
    """Demo reconnect yields a connected mock client."""
    session = ModbusTransportSession(HOST, PORT, demo_mode=True)

    client = await session.reconnect_with_new_client()

    assert isinstance(client, MockModbusTcpClient)
    assert client.connected is True


async def test_real_mode_without_hass_entry_raises() -> None:
    """Real mode without hass/entry has no fallback since the cutover."""
    session = ModbusTransportSession(HOST, PORT)

    assert session._ha_backed is False
    with pytest.raises(ModbusConnectionException):
        await session.ensure_connection()
    with pytest.raises(ModbusConnectionException):
        await session.reconnect_with_new_client()


async def test_ha_path_uses_actual_async_get_ha_unit(monkeypatch) -> None:
    """Sanity: the real async_get_ha_unit is importable and callable shape."""
    assert callable(async_get_ha_unit)


async def test_ensure_connection_reuses_existing_client() -> None:
    """A cached client is returned without touching the provider."""
    session = ModbusTransportSession(HOST, PORT)
    sentinel = object()
    session.client = sentinel

    assert await session.ensure_connection() is sentinel


async def test_ha_provider_error_propagates(monkeypatch) -> None:
    """Unexpected provider failures are logged and re-raised."""
    from modbus_connection.exceptions import ModbusError

    async def failing_get_ha_unit(hass, entry, host, port, unit_id):
        raise ModbusError("provider exploded")

    monkeypatch.setattr(transport_session, "async_get_ha_unit", failing_get_ha_unit)

    session = ModbusTransportSession(
        HOST, PORT, hass=object(), entry=object(), unit_id=UNIT_ID
    )
    with pytest.raises(ModbusError):
        await session.ensure_connection()


async def test_demo_mode_connection_failure_returns_none(monkeypatch) -> None:
    """A failing demo mock yields None instead of raising known errors."""

    class FailingMockClient:
        def __init__(self, host, port):
            pass

        async def connect(self):
            raise OSError("cannot connect mock")

    monkeypatch.setattr(transport_session, "MockModbusTcpClient", FailingMockClient)

    session = ModbusTransportSession(HOST, PORT, demo_mode=True)
    assert await session.ensure_connection() is None
    assert session.client is None


async def test_demo_mode_unexpected_error_propagates(monkeypatch) -> None:
    """Unexpected demo failures are logged and re-raised."""

    class BrokenMockClient:
        def __init__(self, host, port):
            raise RuntimeError("broken factory")

    monkeypatch.setattr(transport_session, "MockModbusTcpClient", BrokenMockClient)

    session = ModbusTransportSession(HOST, PORT, demo_mode=True)
    with pytest.raises(RuntimeError):
        await session.ensure_connection()


async def test_new_client_without_provider_or_demo_raises() -> None:
    """_new_client without hass/entry/demo raises directly."""
    session = ModbusTransportSession(HOST, PORT)
    with pytest.raises(ModbusConnectionException):
        await session._new_client()
