"""Phase-4 tests: repository + mapping on flat-list unit reads.

The ``ModbusConnectionClient`` facade returns flat ``list`` values and
raises the integration hierarchy (translated at the single facade boundary)
instead of returning ``isError()`` response objects. These tests drive the
REAL ``ModbusRegisterRepository`` + ``ModbusMappingTransform`` production
code over a scripted flat-list client:

* optimized batch reads succeed without any ``is_error()`` inspection;
* ``ModbusInvalidAddressException`` (from ``IllegalDataAddressError``) is
  treated as "device does not support this range": holding fallback runs,
  discrete/coils degrade to ``None``, no reconnect retry is spent;
* transient read failures still retry once (discrete/coils/holding chunks);
* writes returning ``None`` (unit ``write_register``/``write_coil`` contract)
  report success with exact address + raw value preserved.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusInvalidAddressException,
    ModbusReadException,
)
from custom_components.ha_daikin_altherma4_modbus.core.mapping_transform import (
    ModbusMappingTransform,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.register_repository import (
    ModbusRegisterRepository,
)


class _FlatClient:
    """Scripted client returning flat lists like ``ModbusConnectionClient``."""

    def __init__(self, results: list) -> None:
        self._results = list(results)
        self.calls: list[tuple[str, int, int]] = []
        self.write_calls: list[tuple[int, int | bool]] = []

    def _next(self):
        outcome = self._results.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def read_holding_registers(self, address: int, count: int):
        self.calls.append(("holding", address, count))
        return self._next()

    async def read_input_registers(self, address: int, count: int):
        self.calls.append(("input", address, count))
        return self._next()

    async def read_discrete_inputs(self, address: int, count: int):
        self.calls.append(("discrete", address, count))
        return self._next()

    async def read_coils(self, address: int, count: int):
        self.calls.append(("coil", address, count))
        return self._next()

    async def write_holding_register(self, address: int, value: int):
        self.write_calls.append((address, value))
        outcome = self._next()
        return outcome

    async def write_coil_register(self, address: int, value: bool):
        self.write_calls.append((address, value))
        outcome = self._next()
        return outcome


class _SessionStub:
    """Minimal session boundary: client + reconnect counting."""

    def __init__(self, client: _FlatClient) -> None:
        self._client = client
        self.reconnect_count = 0

    @property
    def client(self) -> _FlatClient:
        return self._client

    async def ensure_connection(self) -> _FlatClient:
        return self._client

    async def reconnect_with_new_client(self) -> _FlatClient:
        self.reconnect_count += 1
        return self._client


def _repository(
    results: list,
) -> tuple[ModbusRegisterRepository, _FlatClient, _SessionStub]:
    client = _FlatClient(results)
    session = _SessionStub(client)
    return ModbusRegisterRepository(session), client, session


def _item(address: int, name: str):
    return SimpleNamespace(
        address=address,
        register_name=name,
        enum_map=None,
        data_type=None,
        input_type="input",
    )


# --- flat-list batch reads --------------------------------------------------


async def test_input_batch_flat_list_no_is_error_handling() -> None:
    repository, client, session = _repository([[100 + i for i in range(67)]])
    blocks = await repository.read_input_blocks()
    assert client.calls == [("input", 21, 67)]
    assert blocks == [([100 + i for i in range(67)], 21, 87, 21)]
    assert session.reconnect_count == 0


async def test_holding_optimized_flat_list_no_fallback() -> None:
    repository, client, session = _repository([[1] * 80])
    blocks = await repository.read_holding_blocks()
    assert client.calls == [("holding", 1, 80)]
    assert len(blocks) == 1 and len(blocks[0][0]) == 80
    assert session.reconnect_count == 0


async def test_discrete_and_coils_flat_lists() -> None:
    repository, _client, session = _repository([[True] * 26, [False] * 3])
    discrete = await repository.read_discrete_inputs()
    coils = await repository.read_coils()
    assert discrete == [True] * 26
    assert coils == [False] * 3
    assert session.reconnect_count == 0


async def test_mapping_consumes_flat_lists() -> None:
    transform = ModbusMappingTransform()
    # Input block (21-87): offset 21, address 21 -> index 0.
    items = [_item(21, "input_21"), _item(22, "input_22")]
    processed = transform.process_register_block(
        [2500, 2600], items, 21, 87, 21, "input", "Input Register"
    )
    assert processed["input_21"].raw_value == 2500
    assert processed["input_22"].raw_value == 2600
    # Bit lists start at address 1.
    bit_items = [_item(1, "bit_1"), _item(2, "bit_2")]
    bits = transform.process_bit_sensors([True, False], bit_items, "discrete")
    assert bits["bit_1"].value == 1
    assert bits["bit_2"].value == 0


# --- ModbusInvalidAddressException: unsupported range, no retry --------------


async def test_input_invalid_address_degrades_without_retry() -> None:
    repository, _client, session = _repository(
        [ModbusInvalidAddressException("illegal data address")]
    )
    assert await repository.read_input_blocks() == []
    assert session.reconnect_count == 0


async def test_discrete_invalid_address_returns_none_without_retry() -> None:
    repository, _client, session = _repository(
        [ModbusInvalidAddressException("illegal data address")]
    )
    assert await repository.read_discrete_inputs() is None
    assert session.reconnect_count == 0


async def test_holding_invalid_address_runs_fallback_without_retry() -> None:
    chunks = ([100 + i for i in range(25)], [200 + i for i in range(25)])
    repository, _client, session = _repository(
        [
            ModbusInvalidAddressException("big range refused"),
            *chunks,
            ModbusInvalidAddressException("optional block missing"),
        ]
    )
    blocks = await repository.read_holding_blocks()
    assert [b[1] for b in blocks] == [1, 26]
    assert session.reconnect_count == 0


async def test_transient_failure_still_retries_once() -> None:
    repository, _client, session = _repository(
        [ModbusReadException("timeout"), [True] * 26]
    )
    assert await repository.read_discrete_inputs() == [True] * 26
    assert session.reconnect_count == 1


# --- writes: None return means success, address + raw value kept ------------


async def test_write_holding_none_result_reports_success() -> None:
    repository, client = _repository([None])[:2]
    result = await repository.write_holding_register("holding_9", 1)
    assert result is not None
    assert client.write_calls == [(9, 1)]


async def test_write_coil_none_result_reports_success() -> None:
    repository, client = _repository([None])[:2]
    result = await repository.write_coil_register("coil_1", True)
    assert result is not None
    assert client.write_calls == [(1, True)]


async def test_write_propagates_invalid_address() -> None:
    repository, _ = _repository(
        [ModbusInvalidAddressException("illegal data address")]
    )[:2]
    with pytest.raises(ModbusInvalidAddressException):
        await repository.write_holding_register("holding_9", 1)
