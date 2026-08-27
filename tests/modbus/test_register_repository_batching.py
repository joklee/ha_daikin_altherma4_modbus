"""Behavioral regression tests for the register-repository batching logic.

These tests exercise the REAL ``ModbusRegisterRepository`` production code and
only replace the Modbus client boundary underneath it (the session stub also
delegates error detection to the real ``ModbusTransportSession`` helper):

    optimized read  ->  read_holding_registers(address=1, count=80)
          |
          | failure (exception OR protocol error response)
          v
    fallback chunks ->  (1, 25), (26, 25), (51, 30)*   [*optional]
          |
          | EXCEPTION failures additionally trigger one reconnect retry
          v

Protected contracts:
* the optimized single read is attempted first;
* on failure the three chunked reads use the exact documented addresses;
* values of every successful chunk survive once (no loss, no duplicates);
* a failed chunk never aborts the remaining fallback chain;
* protocol-error chunks fail without retry, exception chunks retry once
  after a reconnection attempt;
* a total communication failure degrades in a controlled way
  (empty result instead of fabricated data);
* input registers are read as ONE batch (21, 67) and deliberately have no
  fallback.
"""

from __future__ import annotations

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusReadException,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.register_repository import (
    ModbusRegisterRepository,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.transport_session import (
    ModbusTransportSession,
)

_BIG_READ = (1, 80)
_FALLBACK_BLOCKS = ((1, 25), (26, 25), (51, 30))
_FALLBACK_METADATA = ((1, 25, 1), (26, 50, 26), (51, 80, 51))


class _OkResponse:
    """Successful Modbus response carrying raw register values."""

    def __init__(self, registers: list[int]) -> None:
        self.registers = registers

    def isError(self) -> bool:
        return False


class _ErrorResponse:
    """Protocol-level error response (device refuses the read)."""

    def isError(self) -> bool:
        return True


class _ScriptedClient:
    """Return scripted outcomes in order and record normalized calls."""

    def __init__(self, results: list) -> None:
        self._results = list(results)
        self.calls: list[tuple[int, int]] = []

    async def read_holding_registers(self, address: int, count: int):
        self.calls.append((address, count))
        outcome = self._results.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def read_input_registers(self, address: int, count: int):
        self.calls.append((address, count))
        outcome = self._results.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class _SessionStub:
    """Session boundary consumed by ``ModbusRegisterRepository`` reads.

    Error detection is delegated to the REAL production helper so the tests
    cannot drift from how ``isError()`` responses are classified.
    """

    is_modbus_error = staticmethod(ModbusTransportSession.is_modbus_error)

    def __init__(self, client: _ScriptedClient) -> None:
        self._client = client
        self.reconnect_count = 0

    @property
    def client(self) -> _ScriptedClient:
        return self._client

    async def reconnect_with_new_client(self) -> _ScriptedClient:
        self.reconnect_count += 1
        return self._client


def _repository(
    results: list,
) -> tuple[
    ModbusRegisterRepository,
    _ScriptedClient,
    _SessionStub,
]:
    """Build the real repository on top of a scripted client boundary."""
    client = _ScriptedClient(results)
    session = _SessionStub(client)
    return ModbusRegisterRepository(session), client, session


def _chunk(first_value: int, count: int) -> _OkResponse:
    """Deterministic chunk data, unique per chunk via ``first_value``."""
    return _OkResponse([first_value + i for i in range(count)])


def _flat_registers(blocks) -> list[int]:
    values: list[int] = []
    for block in blocks:
        response = block[0]
        assert isinstance(response, _OkResponse), f"unexpected block: {block!r}"
        values.extend(response.registers)
    return values


def _block_metadata(blocks) -> tuple[tuple[int, int, int], ...]:
    return tuple((block[1], block[2], block[3]) for block in blocks)


# --------------------------------------------------------------------------
# Holding registers: optimized path
# --------------------------------------------------------------------------


async def test_optimized_read_succeeds_without_fallback() -> None:
    """A healthy device answers the single large read; no chunking occurs."""
    repository, client, session = _repository([_chunk(100, 80)])

    blocks = await repository.read_holding_blocks()

    assert client.calls == [_BIG_READ]
    assert len(_flat_registers(blocks)) == 80
    assert _block_metadata(blocks) == ((1, 80, 1),)
    assert session.reconnect_count == 0


# --------------------------------------------------------------------------
# Holding registers: optimized read fails, full fallback chain succeeds
# --------------------------------------------------------------------------


async def test_big_read_exception_runs_complete_fallback_chain() -> None:
    """Large-read exception falls back to all three documented blocks."""
    chunks = (_chunk(100, 25), _chunk(300, 25), _chunk(600, 30))
    repository, client, session = _repository(
        [ModbusReadException("simulated device timeout"), *chunks]
    )

    blocks = await repository.read_holding_blocks()

    assert client.calls == [_BIG_READ, *_FALLBACK_BLOCKS]
    assert _flat_registers(blocks) == [
        *chunks[0].registers,
        *chunks[1].registers,
        *chunks[2].registers,
    ]
    assert _block_metadata(blocks) == _FALLBACK_METADATA
    assert session.reconnect_count == 0


async def test_big_read_protocol_error_runs_fallback_chain() -> None:
    """A refused optimized read triggers the chunked fallback as well."""
    chunks = (_chunk(100, 25), _chunk(300, 25), _chunk(600, 30))
    repository, client, session = _repository([_ErrorResponse(), *chunks])

    blocks = await repository.read_holding_blocks()

    assert client.calls == [_BIG_READ, *_FALLBACK_BLOCKS]
    assert len(_flat_registers(blocks)) == 80
    assert session.reconnect_count == 0


# --------------------------------------------------------------------------
# Holding registers: partial fallback failures keep reachable data
# --------------------------------------------------------------------------


async def test_optional_chunk_protocol_error_is_skipped_without_retry() -> None:
    """A missing optional block must not discard earlier chunk data."""
    chunks = (_chunk(100, 25), _chunk(300, 25))
    repository, client, session = _repository(
        [
            ModbusReadException("big read failed"),
            *chunks,
            _ErrorResponse(),
        ]
    )

    blocks = await repository.read_holding_blocks()

    assert client.calls == [_BIG_READ, *_FALLBACK_BLOCKS]
    assert _flat_registers(blocks) == [*chunks[0].registers, *chunks[1].registers]
    assert session.reconnect_count == 0


async def test_optional_chunk_exception_retries_once_and_recovers() -> None:
    """An exception on the optional block retries once and recovers."""
    chunks = (_chunk(100, 25), _chunk(300, 25), _chunk(600, 30))
    repository, client, session = _repository(
        [
            ModbusReadException("big read failed"),
            *chunks[:2],
            ModbusReadException("transient failure"),
            chunks[2],
        ]
    )

    blocks = await repository.read_holding_blocks()

    assert client.calls == [
        _BIG_READ,
        *_FALLBACK_BLOCKS,
        (51, 30),
    ]
    assert _flat_registers(blocks) == [
        *chunks[0].registers,
        *chunks[1].registers,
        *chunks[2].registers,
    ]
    assert session.reconnect_count == 1


async def test_non_optional_chunk_protocol_error_keeps_remaining_chunks() -> None:
    """Protocol errors fail silently per block; later chunks still arrive."""
    chunks = (_chunk(100, 25), _chunk(300, 25), _chunk(600, 30))
    repository, client, session = _repository(
        [
            _ErrorResponse(),  # big read refused
            _ErrorResponse(),  # block 1 refused (no retry for errors)
            chunks[1],
            chunks[2],
        ]
    )

    blocks = await repository.read_holding_blocks()

    assert client.calls == [_BIG_READ, *_FALLBACK_BLOCKS]
    assert _flat_registers(blocks) == [
        *chunks[1].registers,
        *chunks[2].registers,
    ]
    assert session.reconnect_count == 0


async def test_non_optional_exception_retries_once_chain_continues() -> None:
    """Block-1 exception retries exactly once; remaining chain still runs."""
    chunks = (_chunk(300, 25), _chunk(600, 30))
    repository, client, session = _repository(
        [
            _ErrorResponse(),  # big read refused
            ModbusReadException("block 1 transient"),  # initial read raises
            _ErrorResponse(),  # retry after reconnect fails again
            chunks[0],
            chunks[1],
        ]
    )

    blocks = await repository.read_holding_blocks()

    assert client.calls == [
        _BIG_READ,
        (1, 25),
        (1, 25),
        *_FALLBACK_BLOCKS[1:],
    ]
    assert _flat_registers(blocks) == [*chunks[0].registers, *chunks[1].registers]
    assert session.reconnect_count == 1


# --------------------------------------------------------------------------
# Holding registers: complete communication loss
# --------------------------------------------------------------------------


async def test_total_communication_failure_degrades_controlled() -> None:
    """When nothing can be read, no fabricated data is ever returned."""
    boom = ModbusReadException("device offline")
    repository, client, session = _repository(
        [boom]  # optimized read
        + [boom, boom] * 3  # each fallback block: initial + retry
    )

    blocks = await repository.read_holding_blocks()

    expected_calls: list[tuple[int, int]] = [_BIG_READ]
    for address, count in _FALLBACK_BLOCKS:
        expected_calls.append((address, count))
        expected_calls.append((address, count))
    assert client.calls == expected_calls
    assert blocks == []
    assert session.reconnect_count == 3


# --------------------------------------------------------------------------
# Input registers: single batch without any fallback
# --------------------------------------------------------------------------


async def test_input_registers_single_batch_success() -> None:
    """Healthy devices answer one 67-register batch read covering 21-87."""
    payload = _chunk(200, 67)
    repository, client, session = _repository([payload])

    blocks = await repository.read_input_blocks()

    assert client.calls == [(21, 67)]
    assert _flat_registers(blocks) == payload.registers
    assert _block_metadata(blocks) == ((21, 87, 21),)
    assert session.reconnect_count == 0


@pytest.mark.parametrize(
    ("outcome", "desc"),
    [
        (_ErrorResponse(), "protocol-error"),
        (ModbusReadException("timeout"), "exception"),
    ],
)
async def test_input_registers_have_no_fallback_on_failure(
    outcome: object, desc: str
) -> None:
    """The optimized input read deliberately has no chunked fallback."""
    repository, client, _session = _repository([outcome])

    blocks = await repository.read_input_blocks()

    assert client.calls == [(21, 67)], f"fallback attempted for {desc}"
    assert blocks == [], f"fabricated data returned for {desc}"
