"""Tests for the Phase 3.3 transport-session switch to the HA-backed path.

``ModbusTransportSession`` obtains its client via the HA-backed provider when
``hass``/``entry`` are set (lazy, no I/O) and keeps the legacy real/mock path
otherwise. On the HA path ``reconnect_with_new_client`` must not recreate the
shared connection — it returns the same shared unit.

Skipped when ``modbus-connection`` is not installed.
"""

import pytest

pytest.importorskip("modbus_connection")

from modbus_connection.mock import MockModbusConnection

from custom_components.ha_daikin_altherma4_modbus.modbus import transport_session
from custom_components.ha_daikin_altherma4_modbus.modbus.connection_manager import (
    async_get_ha_unit,
    ensure_modbus_connection,
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


async def test_demo_mode_falls_back_to_legacy_path(monkeypatch) -> None:
    """Demo mode keeps the mock path even when hass/entry are present."""
    ha_called = {"value": False}

    async def fake_get_ha_unit(hass, entry, host, port, unit_id):
        ha_called["value"] = True
        raise AssertionError("HA provider must not be used in demo mode")

    monkeypatch.setattr(transport_session, "async_get_ha_unit", fake_get_ha_unit)

    legacy_calls = {"value": False}
    client_sentinel = object()

    async def fake_ensure_modbus_connection(client, host, port, demo_mode):
        legacy_calls["value"] = True
        return client_sentinel

    monkeypatch.setattr(
        transport_session, "ensure_modbus_connection", fake_ensure_modbus_connection
    )

    session = ModbusTransportSession(
        HOST, PORT, demo_mode=True, hass=object(), entry=object(), unit_id=UNIT_ID
    )

    client = await session.ensure_connection()

    assert ha_called["value"] is False
    assert legacy_calls["value"] is True
    assert client is client_sentinel


async def test_legacy_path_used_without_hass_entry() -> None:
    """Without hass/entry the session reports not HA-backed."""
    session = ModbusTransportSession(HOST, PORT)
    assert session._ha_backed is False


async def test_ha_path_uses_actual_async_get_ha_unit(monkeypatch) -> None:
    """Sanity: the real async_get_ha_unit is importable and callable shape."""
    assert callable(async_get_ha_unit)
    assert callable(ensure_modbus_connection)
