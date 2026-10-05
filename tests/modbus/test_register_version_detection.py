"""Tests for register-map version detection (MMI v2/v3 vs MMI v4.x).

These tests exercise the REAL ``ModbusRegisterRepository`` production code and
only replace the Modbus client boundary underneath it (scripted outcomes per
``(method, address, count)`` call):

* v2/v3 devices (guide 1B/1C) expose discrete input 26, v4 devices (MMI v4.x,
  guide 1D) refuse it with an illegal-data-address error and expose input
  138/139 instead;
* only ``ModbusInvalidAddressException`` (or an ``exception_code=2`` error
  response) counts as "register absent" — transient failures stay undecided;
* probes run at most once (successful conclusions are cached, transient
  failures are retried on the next call);
* version-specific registers are only polled once the map is known: unknown
  (fallback) polls discrete 1-25 and never requests 26/138/139 in batches;
  a refused 1-26 batch still falls back to 1-25 without a reconnect;
* on v4, polling activates the new registers: input 138/139 ride along as
  an extra block and the holding batch grows from 1-80 to 1-81 (with retry
  as 1-80 when 81 is refused); v2/v3 never requests them.
"""

from __future__ import annotations

import logging

from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusInvalidAddressException,
    ModbusTimeoutException,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.register_repository import (
    REGISTER_MAP_V2_V3,
    REGISTER_MAP_V4,
    ModbusRegisterRepository,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.transport_session import (
    ModbusTransportSession,
)


class _OkBits:
    """Successful discrete/coil read carrying raw bit values."""

    def __init__(self, bits: list[bool]) -> None:
        self.bits = bits

    def isError(self) -> bool:
        return False


class _OkRegisters:
    """Successful register read carrying raw register values."""

    def __init__(self, registers: list[int]) -> None:
        self.registers = registers

    def isError(self) -> bool:
        return False


class _IllegalAddressResponse:
    """Protocol-level illegal-data-address refusal (exception_code=2)."""

    def isError(self) -> bool:
        return True

    def __str__(self) -> str:
        return "Modbus Error: [Input/Output] exception_code=2"


class _ScriptedVersionClient:
    """Client with per-call outcomes keyed by (method, address, count)."""

    def __init__(self, outcomes: dict) -> None:
        self._outcomes = dict(outcomes)
        self.calls: list[tuple[str, int, int]] = []

    async def _next(self, method: str, address: int, count: int):
        self.calls.append((method, address, count))
        outcome = self._outcomes[(method, address, count)]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def read_discrete_inputs(self, address: int, count: int):
        return await self._next("discrete", address, count)

    async def read_input_registers(self, address: int, count: int):
        return await self._next("input", address, count)

    async def read_holding_registers(self, address: int, count: int):
        return await self._next("holding", address, count)

    async def read_coils(self, address: int, count: int):
        return await self._next("coil", address, count)


class _SessionStub:
    """Session boundary consumed by ``ModbusRegisterRepository`` reads."""

    is_modbus_error = staticmethod(ModbusTransportSession.is_modbus_error)

    def __init__(self, client: _ScriptedVersionClient) -> None:
        self._client = client
        self.reconnect_count = 0

    @property
    def client(self) -> _ScriptedVersionClient:
        return self._client

    async def reconnect_with_new_client(self) -> _ScriptedVersionClient:
        self.reconnect_count += 1
        return self._client


def _repository(
    outcomes: dict,
) -> tuple[ModbusRegisterRepository, _ScriptedVersionClient, _SessionStub]:
    """Build the real repository on top of a scripted client boundary."""
    client = _ScriptedVersionClient(outcomes)
    session = _SessionStub(client)
    return ModbusRegisterRepository(session), client, session


def _discrete_calls(client: _ScriptedVersionClient) -> list[tuple[int, int]]:
    return [(a, c) for m, a, c in client.calls if m == "discrete"]


async def test_detect_v2_v3_device_reports_version_and_full_batch() -> None:
    repo, client, _ = _repository(
        {
            ("discrete", 26, 1): _OkBits([True]),
            ("input", 138, 2): ModbusInvalidAddressException("illegal address"),
        }
    )
    assert await repo.detect_register_version() == REGISTER_MAP_V2_V3
    assert repo.register_version == REGISTER_MAP_V2_V3
    assert repo._discrete_batch() == (1, 26)

    # Cached: a second detection performs no further reads.
    calls_before = list(client.calls)
    assert await repo.detect_register_version() == REGISTER_MAP_V2_V3
    assert client.calls == calls_before


async def test_detect_v4_device_reports_version_and_reduced_batch() -> None:
    repo, client, _ = _repository(
        {
            ("discrete", 26, 1): ModbusInvalidAddressException("illegal address"),
            ("input", 138, 2): _OkRegisters([0, 0]),
        }
    )
    assert await repo.detect_register_version() == REGISTER_MAP_V4
    assert repo.register_version == REGISTER_MAP_V4
    assert repo._discrete_batch() == (1, 25)

    calls_before = list(client.calls)
    assert await repo.detect_register_version() == REGISTER_MAP_V4
    assert client.calls == calls_before


async def test_unknown_map_polls_without_version_specific_registers() -> None:
    """Fallback: while unknown, batches never request 26/138/139."""
    repo, client, _ = _repository(
        {
            ("discrete", 26, 1): ModbusTimeoutException("timeout"),
            ("input", 138, 2): ConnectionError("dropped"),
            ("discrete", 1, 25): _OkBits([True] * 30),
        }
    )
    assert await repo.detect_register_version() is None
    assert repo.register_version is None
    assert repo._discrete_batch() == (1, 25)

    assert await repo.read_discrete_inputs() is not None
    assert _discrete_calls(client) == [(26, 1), (1, 25)]

    # Transient outcomes are NOT cached: the next call probes again.
    calls_before = list(client.calls)
    assert await repo.detect_register_version() is None
    assert len(client.calls) == len(calls_before) + 2


async def test_ambiguous_devices_report_unknown() -> None:
    # Both present (unexpected) ...
    repo, _, _ = _repository(
        {
            ("discrete", 26, 1): _OkBits([True]),
            ("input", 138, 2): _OkRegisters([0, 0]),
        }
    )
    assert await repo.detect_register_version() is None
    # ... and both absent (unexpected) stay unknown as well.
    repo, _, _ = _repository(
        {
            ("discrete", 26, 1): ModbusInvalidAddressException("no 26"),
            ("input", 138, 2): ModbusInvalidAddressException("no 138"),
        }
    )
    assert await repo.detect_register_version() is None


async def test_protocol_illegal_address_response_counts_as_absent() -> None:
    repo, _, _ = _repository(
        {
            ("discrete", 26, 1): _IllegalAddressResponse(),
            ("input", 138, 2): _OkRegisters([0, 0]),
        }
    )
    assert await repo.detect_register_version() == REGISTER_MAP_V4


async def test_refused_full_batch_falls_back_to_1_25_without_reconnect() -> None:
    # Simulates a map that claimed v2/v3 but refuses 1-26 (e.g. actual v4):
    # the refusal narrows the map and retries as 1-25, no reconnect spent.
    repo, client, session = _repository(
        {
            ("discrete", 1, 26): ModbusInvalidAddressException("illegal address"),
            ("discrete", 1, 25): _OkBits([True] * 25),
        }
    )
    repo._supports_discrete_26 = True
    result = await repo.read_discrete_inputs()
    assert result is not None
    assert _discrete_calls(client) == [(1, 26), (1, 25)]
    # A refused register cannot appear via reconnect: no reconnect attempted.
    assert session.reconnect_count == 0
    assert repo._discrete_batch() == (1, 25)

    # Subsequent polls go straight to the v4 batch.
    client.calls.clear()
    await repo.read_discrete_inputs()
    assert _discrete_calls(client) == [(1, 25)]


async def test_raw_snapshot_uses_detected_map_and_v4_inputs() -> None:
    # Legacy response objects carry 1-based arrays: index == absolute address.
    v4_inputs = [0] * 140
    v4_inputs[138] = 30
    v4_inputs[139] = 2
    v4_holding = [0] * 100
    v4_holding[81] = 1
    repo, client, _ = _repository(
        {
            ("discrete", 26, 1): ModbusInvalidAddressException("no 26"),
            ("input", 138, 2): _OkRegisters(v4_inputs),
            ("input", 21, 67): _OkRegisters([0] * 100),
            ("holding", 1, 81): _OkRegisters(v4_holding),
            ("discrete", 1, 25): _OkBits([True] * 30),
            ("coil", 1, 3): _OkBits([True] * 5),
        }
    )
    assert await repo.detect_register_version() == REGISTER_MAP_V4
    snapshot, failed = await repo.read_raw_snapshot()
    assert failed == {}
    assert _discrete_calls(client) == [(26, 1), (1, 25)]
    # Raw addresses are 0-based: Daikin 138 -> raw 137.
    assert snapshot["input"][137] == 30
    assert snapshot["input"][138] == 2
    # Holding batch grows to 1-81 on v4: Daikin 81 -> raw 80.
    assert snapshot["holding"][80] == 1


async def test_raw_snapshot_without_detection_skips_version_specific() -> None:
    """Fallback snapshot: no 138/139 read, discrete batch is 1-25."""
    repo, client, _ = _repository(
        {
            ("input", 21, 67): _OkRegisters([0] * 100),
            ("holding", 1, 80): _OkRegisters([0] * 100),
            ("discrete", 1, 25): _OkBits([True] * 30),
            ("coil", 1, 3): _OkBits([True] * 5),
        }
    )
    assert repo.register_version is None
    snapshot, failed = await repo.read_raw_snapshot()
    assert failed == {}
    assert _discrete_calls(client) == [(1, 25)]
    input_calls = [(a, c) for m, a, c in client.calls if m == "input"]
    assert input_calls == [(21, 67)]
    assert 137 not in snapshot["input"]


async def test_v4_polling_activates_new_registers() -> None:
    """On REGISTER_MAP_V4, input 138/139 and holding 81 are polled."""
    repo, _client, _ = _repository(
        {
            ("input", 21, 67): _OkRegisters([0] * 100),
            ("input", 138, 2): _OkRegisters([45, 2]),
            ("holding", 1, 81): _OkRegisters([0] * 100),
        }
    )
    repo._supports_discrete_26 = False
    repo._supports_input_138_139 = True
    assert repo.register_version == REGISTER_MAP_V4
    assert repo._holding_batch() == (1, 81)

    input_blocks = await repo.read_input_blocks()
    assert [(block[1], block[2]) for block in input_blocks] == [(21, 87), (138, 139)]

    holding_blocks = await repo.read_holding_blocks()
    assert [(block[1], block[2]) for block in holding_blocks] == [(1, 81)]
    assert repo._supports_holding_81 is True


async def test_v2_v3_polling_never_requests_v4_registers() -> None:
    """On REGISTER_MAP_V2_V3, batches stay at input 21-87 / holding 1-80."""
    repo, client, _ = _repository(
        {
            ("input", 21, 67): _OkRegisters([0] * 100),
            ("holding", 1, 80): _OkRegisters([0] * 100),
        }
    )
    repo._supports_discrete_26 = True
    repo._supports_input_138_139 = False
    assert repo.register_version == REGISTER_MAP_V2_V3
    assert repo._holding_batch() == (1, 80)

    input_blocks = await repo.read_input_blocks()
    assert [(block[1], block[2]) for block in input_blocks] == [(21, 87)]
    holding_blocks = await repo.read_holding_blocks()
    assert [(block[1], block[2]) for block in holding_blocks] == [(1, 80)]

    input_calls = [(a, c) for m, a, c in client.calls if m == "input"]
    assert (138, 2) not in input_calls


async def test_refused_holding_81_batch_falls_back_to_1_80() -> None:
    """A refused 1-81 batch narrows holding 81 and retries as 1-80.

    The input 138/139 finding is left untouched: only the holding-81
    support is narrowed, so the v4 inputs keep polling.
    """
    repo, client, _ = _repository(
        {
            ("holding", 1, 81): ModbusInvalidAddressException("illegal address"),
            ("holding", 1, 80): _OkRegisters([0] * 100),
        }
    )
    repo._supports_input_138_139 = True
    assert repo._holding_batch() == (1, 81)

    holding_blocks = await repo.read_holding_blocks()
    assert [(block[1], block[2]) for block in holding_blocks] == [(1, 80)]
    holding_calls = [(a, c) for m, a, c in client.calls if m == "holding"]
    assert holding_calls == [(1, 81), (1, 80)]
    assert repo._supports_holding_81 is False
    assert repo._supports_input_138_139 is True

    # Subsequent polls go straight to the narrowed 1-80 batch.
    client.calls.clear()
    await repo.read_holding_blocks()
    assert [(a, c) for m, a, c in client.calls if m == "holding"] == [(1, 80)]


async def test_concluded_version_is_logged_once_at_info(caplog) -> None:
    repo, _, _ = _repository(
        {
            ("discrete", 26, 1): ModbusInvalidAddressException("no 26"),
            ("input", 138, 2): _OkRegisters([0, 0]),
        }
    )
    with caplog.at_level(logging.INFO, logger="custom_components"):
        assert await repo.detect_register_version() == REGISTER_MAP_V4
    infos = [
        r
        for r in caplog.records
        if r.levelno == logging.INFO and "register map" in r.message
    ]
    assert len(infos) == 1
    assert "v4" in infos[0].message
    assert "4P773396-1D" in infos[0].message

    # Cached conclusion: no repeat INFO on the next call.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="custom_components"):
        assert await repo.detect_register_version() == REGISTER_MAP_V4
    assert [
        r
        for r in caplog.records
        if r.levelno == logging.INFO and "register map" in r.message
    ] == []


async def test_unknown_version_logs_no_info(caplog) -> None:
    repo, _, _ = _repository(
        {
            ("discrete", 26, 1): ModbusTimeoutException("timeout"),
            ("input", 138, 2): ConnectionError("dropped"),
        }
    )
    with caplog.at_level(logging.INFO, logger="custom_components"):
        assert await repo.detect_register_version() is None
    assert [
        r
        for r in caplog.records
        if r.levelno == logging.INFO and "register map" in r.message
    ] == []
