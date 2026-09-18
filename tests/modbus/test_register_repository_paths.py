"""Path coverage for ModbusRegisterRepository (no HA instance needed).

A programmable fake client drives every read/retry/fallback/write branch:
success, error-result objects, illegal-address, generic transport failures
and missing clients. The session is a stub exposing only what the
repository touches (``client``, ``ensure_connection``,
``reconnect_with_new_client``).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusConnectionException,
    ModbusDeviceException,
    ModbusInvalidAddressException,
    ModbusWriteException,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.register_repository import (
    ModbusRegisterRepository,
    _validate_modbus_address,
)


class _ErrorResponse:
    """Legacy response object signalling a device error."""

    def __init__(self, text="exception_code=2"):
        self._text = text

    def isError(self):
        return True

    def __str__(self):
        return f"ModbusError({self._text})"


def _client(**overrides):
    defaults = {
        "read_input_registers": AsyncMock(return_value=[0] * 67),
        "read_holding_registers": AsyncMock(return_value=[0] * 80),
        "read_discrete_inputs": AsyncMock(return_value=[False] * 26),
        "read_coils": AsyncMock(return_value=[False] * 3),
        "write_holding_register": AsyncMock(return_value=None),
        "write_coil_register": AsyncMock(return_value=None),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _repository(client, reconnect_client=None):
    session = SimpleNamespace(
        client=client,
        ensure_connection=AsyncMock(return_value=client),
        reconnect_with_new_client=AsyncMock(
            return_value=reconnect_client if reconnect_client is not None else client
        ),
    )
    return ModbusRegisterRepository(session), session


def test_validate_modbus_address():
    assert _validate_modbus_address(21) == 21
    assert _validate_modbus_address(0) == 1
    assert _validate_modbus_address(200) == 87
    with pytest.raises(TypeError):
        _validate_modbus_address("21")


def test_signed_conversion_and_scaling_helpers():
    repo, _ = _repository(_client())
    signed = SimpleNamespace(data_type=SimpleNamespace(signed=True, scaling=0.5))
    assert repo._apply_signed_conversion(65535, signed) == -1
    assert repo._apply_signed_conversion(42, None) == 42
    assert repo._apply_signed_conversion(42, SimpleNamespace()) == 42
    assert repo._apply_scaling(100, signed) == 50.0
    assert repo._apply_scaling(100, None) == 100.0


async def test_input_blocks_without_client():
    repo, _ = _repository(None)
    assert await repo.read_input_blocks() == []


async def test_input_blocks_invalid_address_and_generic_error():
    repo, _ = _repository(
        _client(
            read_input_registers=AsyncMock(
                side_effect=ModbusInvalidAddressException("bad")
            )
        )
    )
    assert await repo.read_input_blocks() == []

    repo, _ = _repository(
        _client(
            read_input_registers=AsyncMock(
                side_effect=ModbusConnectionException("down")
            )
        )
    )
    assert await repo.read_input_blocks() == []


async def test_input_blocks_error_result_object():
    repo, _ = _repository(
        _client(read_input_registers=AsyncMock(return_value=_ErrorResponse()))
    )
    assert await repo.read_input_blocks() == []


async def test_discrete_without_client():
    repo, _ = _repository(None)
    assert await repo.read_discrete_inputs() is None


@pytest.mark.parametrize("code", ["exception_code=2", "exception_code=1", "other"])
async def test_discrete_error_result_variants(code):
    repo, _ = _repository(
        _client(read_discrete_inputs=AsyncMock(return_value=_ErrorResponse(code)))
    )
    assert await repo.read_discrete_inputs() is None


async def test_discrete_invalid_address_returns_none():
    repo, _ = _repository(
        _client(
            read_discrete_inputs=AsyncMock(
                side_effect=ModbusInvalidAddressException("bad")
            )
        )
    )
    assert await repo.read_discrete_inputs() is None


async def test_discrete_retry_success():
    failing = _client(
        read_discrete_inputs=AsyncMock(side_effect=ModbusConnectionException("down"))
    )
    repo, _ = _repository(failing, reconnect_client=_client())
    assert await repo.read_discrete_inputs() == [False] * 26


async def test_discrete_retry_without_client():
    failing = _client(
        read_discrete_inputs=AsyncMock(side_effect=ModbusConnectionException("down"))
    )
    repo, _ = _repository(failing, reconnect_client=None)
    assert await repo.read_discrete_inputs() is None


async def test_discrete_retry_invalid_address_and_generic_error():
    failing = _client(
        read_discrete_inputs=AsyncMock(side_effect=ModbusConnectionException("down"))
    )
    bad = _client(
        read_discrete_inputs=AsyncMock(side_effect=ModbusInvalidAddressException("bad"))
    )
    repo, _ = _repository(failing, reconnect_client=bad)
    assert await repo.read_discrete_inputs() is None

    dead = _client(read_discrete_inputs=AsyncMock(side_effect=OSError("still down")))
    repo, _ = _repository(failing, reconnect_client=dead)
    assert await repo.read_discrete_inputs() is None


async def test_discrete_retry_error_result_returns_none():
    failing = _client(
        read_discrete_inputs=AsyncMock(side_effect=ModbusConnectionException("down"))
    )
    erroneous = _client(read_discrete_inputs=AsyncMock(return_value=_ErrorResponse()))
    repo, _ = _repository(failing, reconnect_client=erroneous)
    assert await repo.read_discrete_inputs() is None


async def test_coils_without_client_error_result_and_invalid_address():
    repo, _ = _repository(None)
    assert await repo.read_coils() is None

    repo, _ = _repository(
        _client(read_coils=AsyncMock(return_value=_ErrorResponse("other")))
    )
    assert await repo.read_coils() is None

    repo, _ = _repository(
        _client(read_coils=AsyncMock(side_effect=ModbusInvalidAddressException("bad")))
    )
    assert await repo.read_coils() is None


async def test_coils_retry_success_and_failure():
    failing = _client(
        read_coils=AsyncMock(side_effect=ModbusConnectionException("down"))
    )
    repo, _ = _repository(failing, reconnect_client=_client())
    assert await repo.read_coils() == [False] * 3

    repo, _ = _repository(failing, reconnect_client=None)
    assert await repo.read_coils() is None

    erroneous = _client(read_coils=AsyncMock(return_value=_ErrorResponse()))
    repo, _ = _repository(failing, reconnect_client=erroneous)
    assert await repo.read_coils() is None

    dead = _client(read_coils=AsyncMock(side_effect=OSError("still down")))
    repo, _ = _repository(failing, reconnect_client=dead)
    assert await repo.read_coils() is None

    bad = _client(
        read_coils=AsyncMock(side_effect=ModbusInvalidAddressException("bad"))
    )
    repo, _ = _repository(failing, reconnect_client=bad)
    assert await repo.read_coils() is None


async def test_holding_blocks_without_client():
    repo, _ = _repository(None)
    assert await repo.read_holding_blocks() == []


async def test_holding_blocks_fallback_on_error_result():
    """Error-result batch falls back to chunked blocks."""
    client = _client(read_holding_registers=AsyncMock(return_value=_ErrorResponse()))
    repo, _ = _repository(client)
    blocks = await repo.read_holding_blocks()
    # Fallback chunks return the same error object per chunk -> skipped.
    assert blocks == []
    assert client.read_holding_registers.await_count == 1 + 3


async def test_holding_blocks_fallback_merges_chunks():
    """Fallback chunks merge when the optimized batch is refused."""
    calls = {"count": 0}

    async def read_holding(address, count):
        calls["count"] += 1
        if address == 1 and count == 80:
            raise ModbusInvalidAddressException("no batch")
        return [address] * count

    client = _client(read_holding_registers=read_holding)
    repo, _ = _repository(client)
    blocks = await repo.read_holding_blocks()
    assert len(blocks) == 3
    assert [(start, end) for _, start, end, _ in blocks] == [
        (1, 25),
        (26, 50),
        (51, 80),
    ]


async def test_holding_block_client_none_and_optional_skip():
    repo = ModbusRegisterRepository(SimpleNamespace(client=None))
    assert (
        await repo._read_holding_register_block(1, 25, 1, 25, 1, "Block 1", False)
        is None
    )


async def test_holding_retry_without_client():
    repo = ModbusRegisterRepository(
        SimpleNamespace(
            client=_client(),
            ensure_connection=AsyncMock(),
            reconnect_with_new_client=AsyncMock(return_value=None),
        )
    )
    assert await repo._retry_holding_block(1, 25, 1, 25, 1, "Block 1", False) is None


async def test_holding_retry_error_result_optional_and_required():
    failing = _client(
        read_holding_registers=AsyncMock(side_effect=ModbusConnectionException("down"))
    )
    erroneous = _client(read_holding_registers=AsyncMock(return_value=_ErrorResponse()))
    repo, _ = _repository(failing, reconnect_client=erroneous)
    assert await repo._retry_holding_block(1, 25, 1, 25, 1, "Block 1", True) is None
    assert await repo._retry_holding_block(1, 25, 1, 25, 1, "Block 1", False) is None


async def test_holding_retry_invalid_address_and_generic_error():
    client = _client()
    bad = _client(
        read_holding_registers=AsyncMock(
            side_effect=ModbusInvalidAddressException("bad")
        )
    )
    repo, _ = _repository(client, reconnect_client=bad)
    assert await repo._retry_holding_block(1, 25, 1, 25, 1, "Block 1", False) is None

    dead = _client(read_holding_registers=AsyncMock(side_effect=OSError("down")))
    repo, _ = _repository(client, reconnect_client=dead)
    assert await repo._retry_holding_block(1, 25, 1, 25, 1, "Block 1", False) is None


async def test_write_holding_no_client_and_bad_name():
    repo, _ = _repository(None)
    with pytest.raises(ModbusConnectionException):
        await repo.write_holding_register("holding_3", 1)

    repo, _ = _repository(_client())
    with pytest.raises(ValueError):
        await repo.write_holding_register("holding", 1)


async def test_write_holding_signed_conversion_and_success():
    client = _client()
    repo, _ = _repository(client)
    assert await repo.write_holding_register("holding_54", -5) is True
    client.write_holding_register.assert_awaited_once_with(54, 65531)


async def test_write_holding_error_result_and_unexpected_error():
    repo, _ = _repository(
        _client(write_holding_register=AsyncMock(return_value=_ErrorResponse()))
    )
    with pytest.raises(ModbusDeviceException):
        await repo.write_holding_register("holding_3", 1)

    repo, _ = _repository(
        _client(write_holding_register=AsyncMock(side_effect=RuntimeError("weird")))
    )
    with pytest.raises(ModbusWriteException):
        await repo.write_holding_register("holding_3", 1)

    repo, _ = _repository(
        _client(
            write_holding_register=AsyncMock(
                side_effect=ModbusConnectionException("down")
            )
        )
    )
    with pytest.raises(ModbusConnectionException):
        await repo.write_holding_register("holding_3", 1)


async def test_write_coil_paths():
    repo, _ = _repository(None)
    with pytest.raises(ModbusConnectionException):
        await repo.write_coil_register("coil_1", True)

    client = _client()
    repo, _ = _repository(client)
    assert await repo.write_coil_register("coil_1", True) is True
    assert await repo.write_coil_register(2, False) is True
    with pytest.raises(ValueError):
        await repo.write_coil_register("coil_x", True)
    with pytest.raises(ValueError):
        await repo.write_coil_register(2.5, True)

    repo, _ = _repository(
        _client(write_coil_register=AsyncMock(return_value=_ErrorResponse()))
    )
    with pytest.raises(ModbusDeviceException):
        await repo.write_coil_register("coil_1", True)

    repo, _ = _repository(
        _client(write_coil_register=AsyncMock(side_effect=RuntimeError("weird")))
    )
    with pytest.raises(ModbusWriteException):
        await repo.write_coil_register("coil_1", True)

    repo, _ = _repository(
        _client(
            write_coil_register=AsyncMock(side_effect=ModbusConnectionException("down"))
        )
    )
    with pytest.raises(ModbusConnectionException):
        await repo.write_coil_register("coil_1", True)


async def test_snapshot_without_client_and_with_space_failure():
    repo, _ = _repository(None)
    snapshot, failed = await repo.read_raw_snapshot()
    assert snapshot == {"holding": {}, "input": {}, "coil": {}, "discrete": {}}
    assert set(failed) == {"holding", "input", "coil", "discrete"}

    failing_input = _client(
        read_input_registers=AsyncMock(side_effect=ModbusConnectionException("down"))
    )
    repo, _ = _repository(failing_input)
    snapshot, failed = await repo.read_raw_snapshot()
    assert "input" in failed
    assert snapshot["holding"] != {}
    assert snapshot["coil"] != {}
    assert snapshot["discrete"] != {}


async def test_snapshot_unexpected_exception_recorded():
    client = _client(read_input_registers=AsyncMock(side_effect=RuntimeError("weird")))
    repo, _ = _repository(client)
    _, failed = await repo.read_raw_snapshot()
    assert "input" in failed
