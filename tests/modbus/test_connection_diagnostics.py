"""Tests for the modbus-connection diagnostic entities ("Enhanced" device).

Covers the full chain behind the diagnostic entities:

* facade / demo mock stamp ``last_read_at`` / ``last_write_at`` on success
  only (the ``ModbusUnit`` itself holds no state);
* the facade counts failures by direction and category and remembers the
  newest failure (neither the unit nor HA's shared component expose
  diagnostics);
* ``CoordinatorManager`` aggregates connection status, newest timestamps,
  and error totals;
* the entities serve those values live (timestamps as ``TIMESTAMP`` sensors,
  connection status as a ``connectivity`` binary sensor, error totals as
  counters with a per-category breakdown).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("modbus_connection")

from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection

from custom_components.ha_daikin_altherma4_modbus.entities import (
    binary_sensor as binary_platform,
)
from custom_components.ha_daikin_altherma4_modbus.entities import (
    sensor as sensor_platform,
)
from custom_components.ha_daikin_altherma4_modbus.entities.binary_sensor import (
    ConnectionActiveSensor,
)
from custom_components.ha_daikin_altherma4_modbus.entities.sensor import (
    ConnectionErrorSensor,
    ConnectionStateSensor,
    ConnectionTimestampSensor,
)
from custom_components.ha_daikin_altherma4_modbus.integration.coordinator_manager import (
    CoordinatorManager,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.mock_client import (
    MockModbusTcpClient,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.modbus_connection_client import (
    ModbusConnectionClient,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.register_repository import (
    ModbusRegisterRepository,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.transport_session import (
    ModbusTransportSession,
)


def _facade() -> tuple[MockModbusConnection, ModbusConnectionClient]:
    connection = MockModbusConnection()
    return connection, ModbusConnectionClient(connection, unit_id=1)


# --- facade / mock stamping -------------------------------------------------


async def test_facade_stamps_last_read_on_success() -> None:
    _, client = _facade()
    assert client.last_read_at is None

    await client.read_holding_registers(6, 1)

    assert client.last_read_at is not None
    assert client.last_write_at is None


async def test_facade_stamps_last_write_on_success() -> None:
    _, client = _facade()

    await client.write_holding_register(11, 42)

    assert client.last_write_at is not None
    assert client.last_read_at is None


async def test_facade_does_not_stamp_failed_read() -> None:
    connection, client = _facade()
    connection.for_unit(1).fail_read(20, ModbusError("boom"), register_type="input")

    with pytest.raises(Exception):
        await client.read_input_registers(21, 1)

    assert client.last_read_at is None


async def test_mock_client_stamps_read_and_write() -> None:
    client = MockModbusTcpClient("192.168.1.100", 502)
    await client.connect()

    await client.read_input_registers(21, 1)
    assert client.last_read_at is not None
    assert client.last_write_at is None

    await client.write_coil_register(1, True)
    assert client.last_write_at is not None


# --- manager aggregation ----------------------------------------------------


def _manager(normal_client, slow_client) -> CoordinatorManager:
    """Build a manager shell with stubbed coordinators (no hass needed)."""
    manager = CoordinatorManager.__new__(CoordinatorManager)
    manager.normal_coordinator = SimpleNamespace(
        data_manager=SimpleNamespace(client=normal_client)
    )
    manager.slow_coordinator = SimpleNamespace(
        data_manager=SimpleNamespace(client=slow_client)
    )
    manager.coordinators = {
        "normal": manager.normal_coordinator,
        "slow": manager.slow_coordinator,
    }
    return manager


def test_connection_active_true_when_any_client_connected() -> None:
    class _Client:
        connected = False

    manager = _manager(_Client(), _Client())
    assert manager.connection_active is False

    class _LiveClient:
        connected = True

    manager = _manager(_Client(), _LiveClient())
    assert manager.connection_active is True


def test_connection_active_false_without_clients() -> None:
    manager = _manager(None, None)
    assert manager.connection_active is False


def test_last_read_takes_newest_stamp() -> None:
    manager = _manager(
        SimpleNamespace(connected=True, last_read_at=100.0, last_write_at=None),
        SimpleNamespace(connected=True, last_read_at=200.0, last_write_at=50.0),
    )
    assert manager.last_read_at == 200.0
    assert manager.last_write_at == 50.0


def test_last_stamps_none_when_nothing_reported() -> None:
    manager = _manager(
        SimpleNamespace(connected=True),
        SimpleNamespace(connected=False),
    )
    assert manager.last_read_at is None
    assert manager.last_write_at is None


# --- entities ----------------------------------------------------------------


def _coordinator(manager) -> SimpleNamespace:
    return SimpleNamespace(manager=manager, data={})


def test_active_sensor_reports_manager_state() -> None:
    entity = ConnectionActiveSensor(
        coordinator=_coordinator(
            _manager(SimpleNamespace(connected=False), SimpleNamespace(connected=True))
        ),
        entry=None,
        unique_id="connection_active",
        translation_key="connection_active",
        device_info=None,
    )
    assert entity.available is True
    assert entity.is_on is True


def test_active_sensor_available_without_connection() -> None:
    entity = ConnectionActiveSensor(
        coordinator=_coordinator(_manager(None, None)),
        entry=None,
        unique_id="connection_active",
        translation_key="connection_active",
        device_info=None,
    )
    # Still available: reporting "off" is the sensor's purpose.
    assert entity.available is True
    assert entity.is_on is False


def test_timestamp_sensor_unknown_before_first_read() -> None:
    entity = ConnectionTimestampSensor(
        coordinator=_coordinator(_manager(None, None)),
        entry=None,
        unique_id="connection_last_read",
        stamp_kind="read",
        device_class="timestamp",
        translation_key="connection_last_read",
    )
    assert entity.available is False
    assert entity.native_value is None


def test_timestamp_sensor_reports_newest_read() -> None:
    entity = ConnectionTimestampSensor(
        coordinator=_coordinator(
            _manager(
                SimpleNamespace(
                    connected=True, last_read_at=1700000000.0, last_write_at=None
                ),
                SimpleNamespace(
                    connected=True, last_read_at=1700000100.0, last_write_at=None
                ),
            )
        ),
        entry=None,
        unique_id="connection_last_read",
        stamp_kind="read",
        device_class="timestamp",
        translation_key="connection_last_read",
    )
    assert entity.available is True
    value = entity.native_value
    assert value is not None
    assert value.isoformat() == "2023-11-14T22:15:00+00:00"


def test_timestamp_sensor_write_kind_uses_write_stamp() -> None:
    entity = ConnectionTimestampSensor(
        coordinator=_coordinator(
            _manager(
                SimpleNamespace(
                    connected=True,
                    last_read_at=1700000000.0,
                    last_write_at=1700000200.0,
                ),
                SimpleNamespace(connected=True),
            )
        ),
        entry=None,
        unique_id="connection_last_write",
        stamp_kind="write",
        device_class="timestamp",
        translation_key="connection_last_write",
    )
    assert entity.available is True
    assert entity.native_value is not None
    assert entity.native_value.isoformat() == "2023-11-14T22:16:40+00:00"


# --- error counting ---------------------------------------------------------


async def test_facade_counts_read_errors_by_category() -> None:
    connection, client = _facade()
    unit = connection.for_unit(1)
    unit.fail_read(20, ModbusTimeoutError("timed out"), register_type="input")
    unit.fail_read(21, ModbusConnectionError("lost"), register_type="input")
    unit.fail_read(22, IllegalDataAddressError("bad address"), register_type="input")
    unit.fail_read(23, ModbusError("generic"), register_type="input")

    for raw_address in (20, 21, 22, 23):
        with pytest.raises(Exception):
            await client.read_input_registers(raw_address + 1, 1)

    assert client.error_counts["read_timeout"] == 1
    assert client.error_counts["read_connection"] == 1
    assert client.error_counts["read_invalid_address"] == 1
    assert client.error_counts["read_other"] == 1
    assert client.error_counts["write_timeout"] == 0
    assert client.last_error_at is not None
    assert "read at 24" in client.last_error
    assert "ModbusError" in client.last_error


async def test_facade_counts_write_errors() -> None:
    connection, client = _facade()
    connection.for_unit(1).fail_write(10, ModbusTimeoutError("timed out"))

    with pytest.raises(Exception):
        await client.write_holding_register(11, 42)

    assert client.error_counts["write_timeout"] == 1
    assert client.error_counts["read_timeout"] == 0
    assert client.last_error_at is not None


async def test_facade_success_does_not_count_errors() -> None:
    _, client = _facade()
    await client.read_holding_registers(6, 1)
    await client.write_holding_register(11, 42)

    assert sum(client.error_counts.values()) == 0
    assert client.last_error is None
    assert client.last_error_at is None


def test_manager_aggregates_error_breakdown() -> None:
    manager = _manager(
        SimpleNamespace(
            connected=True,
            error_counts={
                "read_timeout": 2,
                "read_connection": 1,
                "read_invalid_address": 0,
                "read_other": 0,
                "write_timeout": 0,
                "write_connection": 0,
                "write_invalid_address": 3,
                "write_other": 0,
            },
            last_error_at=1700000000.0,
            last_error="read at 21: ModbusTimeoutError: timed out",
        ),
        SimpleNamespace(
            connected=True,
            error_counts={
                "read_timeout": 1,
                "read_connection": 0,
                "read_invalid_address": 0,
                "read_other": 4,
                "write_timeout": 0,
                "write_connection": 0,
                "write_invalid_address": 0,
                "write_other": 0,
            },
            last_error_at=1700000100.0,
            last_error="read at 22: ModbusError: generic",
        ),
    )
    assert manager.read_errors == 8
    assert manager.write_errors == 3
    assert manager.error_breakdown("read") == {
        "timeout": 3,
        "connection": 1,
        "invalid_address": 0,
        "other": 4,
    }
    assert manager.last_error_at == 1700000100.0
    assert manager.last_error == "read at 22: ModbusError: generic"


def test_manager_error_totals_zero_without_clients() -> None:
    manager = _manager(None, None)
    assert manager.read_errors == 0
    assert manager.write_errors == 0
    assert manager.last_error is None
    assert manager.last_error_at is None


def test_error_sensor_reports_totals_and_breakdown() -> None:
    entity = ConnectionErrorSensor(
        coordinator=_coordinator(
            _manager(
                SimpleNamespace(
                    connected=True,
                    error_counts={
                        "read_timeout": 2,
                        "read_connection": 0,
                        "read_invalid_address": 1,
                        "read_other": 0,
                        "write_timeout": 0,
                        "write_connection": 0,
                        "write_invalid_address": 0,
                        "write_other": 0,
                    },
                    last_error_at=1700000000.0,
                    last_error="read at 21: ModbusTimeoutError: timed out",
                ),
                SimpleNamespace(connected=True),
            )
        ),
        entry=None,
        unique_id="connection_read_errors",
        error_kind="read",
        translation_key="connection_read_errors",
    )
    assert entity.available is True
    assert entity.native_value == 3
    attributes = entity.extra_state_attributes
    assert attributes["timeout"] == 2
    assert attributes["invalid_address"] == 1
    assert attributes["connection"] == 0
    assert attributes["other"] == 0
    assert attributes["last_error"] == "read at 21: ModbusTimeoutError: timed out"
    assert attributes["last_error_at"] == "2023-11-14T22:13:20+00:00"


def test_write_error_sensor_starts_at_zero() -> None:
    entity = ConnectionErrorSensor(
        coordinator=_coordinator(_manager(None, None)),
        entry=None,
        unique_id="connection_write_errors",
        error_kind="write",
        translation_key="connection_write_errors",
    )
    assert entity.available is True
    assert entity.native_value == 0


# --- connection state -------------------------------------------------------


def test_state_sensor_reports_connected() -> None:
    entity = ConnectionStateSensor(
        coordinator=_coordinator(
            _manager(SimpleNamespace(connected=False), SimpleNamespace(connected=True))
        ),
        entry=None,
        unique_id="connection_state",
        translation_key="connection_state",
    )
    assert entity.available is True
    assert entity.native_value == "connected"


def test_state_sensor_reports_disconnected() -> None:
    entity = ConnectionStateSensor(
        coordinator=_coordinator(_manager(None, None)),
        entry=None,
        unique_id="connection_state",
        translation_key="connection_state",
    )
    # Still available: reporting "disconnected" is the sensor's purpose.
    assert entity.available is True
    assert entity.native_value == "disconnected"


def test_state_sensor_unavailable_without_manager() -> None:
    entity = ConnectionStateSensor(
        coordinator=SimpleNamespace(manager=None, data={}),
        entry=None,
        unique_id="connection_state",
        translation_key="connection_state",
    )
    assert entity.available is False
    assert entity.native_value is None


# --- mock-backend patterns (testing-guide) ----------------------------------


def _live_repository() -> tuple[
    MockModbusConnection, ModbusRegisterRepository, ModbusConnectionClient
]:
    """Real facade + real repository over a seeded mock connection."""
    connection = MockModbusConnection()
    client = ModbusConnectionClient(connection=connection, unit_id=1)
    session = ModbusTransportSession("192.168.1.100", 502)
    session.client = client
    return connection, ModbusRegisterRepository(session), client


async def test_poll_issues_documented_batches_end_to_end() -> None:
    """`read_events` pins batch addresses through the real facade path.

    The scripted-client tests assert what the repository *asks for*; this
    asserts what actually reaches the wire (1-based Daikin addresses
    translated to raw 0-based blocks) for all four poll reads.
    """
    connection, repository, _ = _live_repository()
    unit = connection.for_unit(1)
    unit.input[20] = 2500
    unit.holding[0] = 42
    unit.discrete_inputs[0] = True
    unit.coils[0] = True

    input_blocks = await repository.read_input_blocks()
    holding_blocks = await repository.read_holding_blocks()
    discrete = await repository.read_discrete_inputs()
    coils = await repository.read_coils()

    assert [(block[1], block[2]) for block in input_blocks] == [(21, 87)]
    assert [(block[1], block[2]) for block in holding_blocks] == [(1, 80)]
    assert discrete is not None and coils is not None

    issued = {
        (event.register_type, event.address, event.count) for event in unit.read_events
    }
    assert ("input", 20, 67) in issued  # Daikin 21..87 -> raw 20, 67 regs
    assert ("holding", 0, 80) in issued  # Daikin 1..80 -> raw 0, 80 regs
    # modbus-connection>=4.11 records discrete reads as "discrete"
    # (older: "discrete_input"); pin the batch address either way.
    assert ("discrete_input", 0, 26) in issued or ("discrete", 0, 26) in issued
    assert ("coil", 0, 3) in issued  # Daikin 1..3 -> raw 0


async def test_total_outage_degrades_and_recovers() -> None:
    """`fail_requests` models a dead device without address knowledge."""
    connection, repository, client = _live_repository()
    connection.for_unit(1).fail_requests(ModbusConnectionError("dead gateway"))

    assert await repository.read_input_blocks() == []
    assert await repository.read_discrete_inputs() is None
    # One facade call per read (input has no retry; the discrete retry never
    # reaches the facade because reconnect raises first).
    assert client.error_counts["read_connection"] == 2
    assert client.last_read_at is None

    connection.for_unit(1).fail_requests(None)
    connection.for_unit(1).input[20] = 2500

    blocks = await repository.read_input_blocks()
    assert len(blocks) == 1
    assert client.last_read_at is not None


async def test_dropped_link_reconnects_on_next_read() -> None:
    """`simulate_connection_lost` drops the link; the next read reopens it."""
    connection = MockModbusConnection()
    connection.for_unit(1).input[20] = 2500
    client = ModbusConnectionClient(connection=connection, unit_id=1)

    assert await client.read_input_registers(21, 1) == [2500]
    assert client.connected is True

    connection.simulate_connection_lost()
    assert client.connected is False

    # Same facade handle stays valid and reconnects on demand.
    assert await client.read_input_registers(21, 1) == [2500]
    assert client.connected is True


async def test_disconnect_owned_connection_drops_link() -> None:
    """Disconnect on an owned connection drops the link (HA units: no-op)."""
    connection = MockModbusConnection()
    client = ModbusConnectionClient(connection=connection, unit_id=1)
    await client.connect()
    assert connection.connected is True

    await client.disconnect()

    assert connection.connected is False


# --- platform setup wiring --------------------------------------------------


def _setup_entry(coordinator) -> SimpleNamespace:
    return SimpleNamespace(
        entry_id="test",
        data={},
        options={},
        runtime_data=SimpleNamespace(coordinator=coordinator),
    )


async def test_binary_setup_creates_active_sensor() -> None:
    """The binary platform wires exactly one Enhanced active sensor."""
    from homeassistant.components.binary_sensor import (
        BinarySensorDeviceClass as BinaryDeviceClass,
    )
    from homeassistant.const import EntityCategory as HACategory

    coordinator = SimpleNamespace(data={}, manager=None)
    added: list = []
    await binary_platform.async_setup_entry(
        SimpleNamespace(), _setup_entry(coordinator), added.extend
    )

    active = [e for e in added if isinstance(e, ConnectionActiveSensor)]
    assert len(active) == 1
    entity = active[0]
    assert (
        entity._attr_device_info["translation_key"]
        == "daikin_altherma_modbus_calculated_sensors"
    )
    assert entity._attr_device_class == BinaryDeviceClass.CONNECTIVITY
    assert entity._attr_entity_category == HACategory.DIAGNOSTIC
    assert entity._attr_translation_key == "connection_active"


async def test_sensor_setup_creates_connection_entities() -> None:
    """The sensor platform wires timestamps, counters, and state sensors."""
    manager = _manager(
        SimpleNamespace(
            connected=True,
            last_read_at=1700000000.0,
            last_write_at=1700000200.0,
            error_counts={},
            last_error_at=None,
            last_error=None,
        ),
        SimpleNamespace(connected=False),
    )
    coordinator = SimpleNamespace(
        data={}, manager=manager, async_add_listener=lambda *args: None
    )
    added: list = []
    await sensor_platform.async_setup_entry(
        SimpleNamespace(), _setup_entry(coordinator), added.extend
    )

    stamps = [e for e in added if isinstance(e, ConnectionTimestampSensor)]
    errors = [e for e in added if isinstance(e, ConnectionErrorSensor)]
    states = [e for e in added if isinstance(e, ConnectionStateSensor)]
    assert len(stamps) == 2
    assert len(errors) == 2
    assert len(states) == 1
    # Gold entity-disabled-by-default: deep-dive timestamps/counters start
    # disabled, the headline state sensor stays enabled.
    assert all(e.entity_registry_enabled_default is False for e in stamps)
    assert all(e.entity_registry_enabled_default is False for e in errors)
    assert all(e.entity_registry_enabled_default is True for e in states)
    assert {e._stamp_kind for e in stamps} == {"read", "write"}
    assert {e._error_kind for e in errors} == {"read", "write"}
    # Values resolve live from the manager through the real setup path.
    by_id = {e._attr_unique_id: e for e in (*stamps, *errors, *states)}
    assert by_id["connection_last_read"].native_value is not None
    assert by_id["connection_state"].native_value == "connected"
    assert by_id["connection_read_errors"].native_value == 0
