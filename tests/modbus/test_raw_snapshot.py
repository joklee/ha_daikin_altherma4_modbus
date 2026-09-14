"""Tests for raw register snapshots (diagnostics download support).

``ModbusRegisterRepository.read_raw_snapshot`` performs fresh reads of all
four spaces and returns them keyed by raw 0-based unit address
(Daikin address = raw + 1), plus a per-space failed map. The shape is
directly ``load_raw``-compatible so a snapshot from a bug report replays
into the mock backend.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("modbus_connection")

from modbus_connection.exceptions import ModbusConnectionError
from modbus_connection.mock import MockModbusConnection

from custom_components.ha_daikin_altherma4_modbus.integration.diagnostics import (
    async_get_config_entry_diagnostics,
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


def _repository(connection) -> tuple[ModbusRegisterRepository, ModbusConnectionClient]:
    """Real facade + real repository over the given mock connection."""
    client = ModbusConnectionClient(connection=connection, unit_id=1)
    session = ModbusTransportSession("192.168.1.100", 502)
    session.client = client
    return ModbusRegisterRepository(session), client


async def test_snapshot_shape_and_raw_keying() -> None:
    """Snapshot maps all four spaces by raw address, values undecoded."""
    connection = MockModbusConnection()
    unit = connection.for_unit(1)
    unit.input[20] = 2500
    unit.input[50] = 32767  # special values pass through raw
    unit.holding[0] = 42
    unit.discrete_inputs[0] = True
    unit.coils[0] = True
    repository, _ = _repository(connection)

    snapshot, failed = await repository.read_raw_snapshot()

    assert failed == {}
    assert len(snapshot["input"]) == 67
    assert snapshot["input"][20] == 2500
    assert snapshot["input"][50] == 32767
    assert len(snapshot["holding"]) == 80
    assert snapshot["holding"][0] == 42
    assert len(snapshot["discrete"]) == 26
    assert snapshot["discrete"][0] is True
    assert len(snapshot["coil"]) == 3
    assert snapshot["coil"][0] is True


async def test_snapshot_collects_failures_per_space() -> None:
    """A dead device yields empty maps plus one failure per space."""
    connection = MockModbusConnection()
    repository, client = _repository(connection)
    connection.for_unit(1).fail_requests(ModbusConnectionError("dead gateway"))

    snapshot, failed = await repository.read_raw_snapshot()

    assert all(values == {} for values in snapshot.values())
    assert set(failed) == {"holding", "input", "coil", "discrete"}
    # The repository surfaces the translated integration exception.
    assert "ModbusConnectionException" in failed["input"]
    # Failures are counted at the facade boundary as usual: input (1) +
    # holding big read (1) + holding chunks (3) + discrete (1) + coils (1).
    assert client.error_counts["read_connection"] == 7


async def test_snapshot_merges_holding_fallback_with_note() -> None:
    """A refused big read falls back to chunks; partial data keeps its note."""
    connection = MockModbusConnection()
    repository, _ = _repository(connection)
    # Raw 60 sits inside the big (1, 80) read and chunk (51, 30) only.
    connection.for_unit(1).fail_read(60, ModbusConnectionError("refused"))

    snapshot, failed = await repository.read_raw_snapshot()

    assert len(snapshot["holding"]) == 50  # chunks (1, 25) + (26, 25)
    assert snapshot["holding"][0] is not None
    assert "holding" in failed  # partial data still carries its error note
    assert "input" not in failed


async def test_snapshot_replays_via_load_raw() -> None:
    """A snapshot loads into a fresh mock and reads back identically."""
    connection = MockModbusConnection()
    unit = connection.for_unit(1)
    unit.input[20] = 2500
    unit.holding[0] = 42
    repository, _ = _repository(connection)

    snapshot, failed = await repository.read_raw_snapshot()
    assert failed == {}

    fresh = MockModbusConnection()
    fresh.for_unit(1).load_raw(snapshot)
    fresh_repository, _ = _repository(fresh)

    blocks = await fresh_repository.read_input_blocks()
    assert [value for value in blocks[0][0]] == [
        snapshot["input"][address] for address in range(20, 87)
    ]
    holding_blocks = await fresh_repository.read_holding_blocks()
    assert [value for value in holding_blocks[0][0]] == [
        snapshot["holding"][address] for address in range(80)
    ]


async def test_snapshot_over_demo_mock() -> None:
    """The legacy response-object path normalizes to the same shape."""
    session = ModbusTransportSession("192.168.1.100", 502, demo_mode=True)
    await session.ensure_connection()
    repository = ModbusRegisterRepository(session)

    snapshot, failed = await repository.read_raw_snapshot()

    assert failed == {}
    # Legacy 1-based arrays carry one trailing filler past the block; the
    # requested ranges themselves map exactly (raw = Daikin - 1).
    assert len(snapshot["input"]) >= 67
    assert len(snapshot["holding"]) >= 80
    assert len(snapshot["discrete"]) >= 26
    assert len(snapshot["coil"]) >= 3
    # Spot check: mock demo value for Daikin input 40 is raw 3250.
    assert snapshot["input"][39] == 3250


async def test_diagnostics_download_has_guide_shape() -> None:
    """Download carries registers, failed, and updated keys."""
    coord = SimpleNamespace(
        data={},
        last_update_success=True,
        update_interval=None,
        data_manager=SimpleNamespace(
            read_raw_snapshot=AsyncMock(
                return_value=(
                    {"holding": {}, "input": {20: 2500}, "coil": {}, "discrete": {}},
                    {"coil": "ModbusConnectionError: dead gateway"},
                )
            ),
        ),
    )
    entry = SimpleNamespace(
        data={"host": "192.168.1.100", "port": 502},
        options={},
        runtime_data=SimpleNamespace(
            manager=SimpleNamespace(
                host="192.168.1.100",
                port=502,
                demo_mode=False,
                coordinators={"normal": coord},
            )
        ),
    )

    result = await async_get_config_entry_diagnostics(SimpleNamespace(), entry)

    assert result["registers"]["input"] == {20: 2500}
    assert result["failed"] == {"coil": "ModbusConnectionError: dead gateway"}
    assert result["updated"] == ["input"]
