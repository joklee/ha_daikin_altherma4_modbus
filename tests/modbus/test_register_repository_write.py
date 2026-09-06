"""Behavioral regression tests for the register-repository WRITE path.

These tests exercise the REAL ``ModbusRegisterRepository.write_holding_register``
production code and only replace the Modbus client boundary underneath it:

    select/number service value  ->  write_holding_register(name, value)
          |
          |  register config lookup (signedness detection)
          v
    raw Modbus write  ->  client.write_holding_registers(address, raw_value)

Protected contracts:
* writing a select register resolves the register configuration and sends the
  raw value to the exact documented Modbus address
  (regression: a stale function-level import raised ``ModuleNotFoundError``
  for ``...modbus.common`` on every holding-register write, so option changes
  on e.g. ``holding_9`` / ``holding_68`` failed at runtime while reads worked);
* negative values for signed registers are converted to 16-bit two's
  complement before transmission;
* non-negative values are transmitted unchanged;
* a protocol-error response is raised as ``ModbusDeviceException`` and never
  reported as success;
* ``get_register_config`` resolves the default holding-register list without
  an explicit argument (regression: stale import of the restructured
  register-constants module).
"""

from __future__ import annotations

import pytest

from custom_components.ha_daikin_altherma4_modbus.common.helpers import (
    get_register_config,
)
from custom_components.ha_daikin_altherma4_modbus.core.exceptions import (
    ModbusDeviceException,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.register_repository import (
    ModbusRegisterRepository,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.transport_session import (
    ModbusTransportSession,
)


class _OkResponse:
    """Successful Modbus write response."""

    def isError(self) -> bool:
        return False


class _ErrorResponse:
    """Protocol-level error response (device refuses the write)."""

    def isError(self) -> bool:
        return True


class _ScriptedWriteClient:
    """Record normalized write calls and return scripted outcomes."""

    def __init__(self, result) -> None:
        self._result = result
        self.write_calls: list[tuple[int, int]] = []

    async def write_holding_register(self, address: int, value: int):
        self.write_calls.append((address, value))
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class _SessionStub:
    """Session boundary consumed by ``ModbusRegisterRepository`` writes.

    Error detection is delegated to the REAL production helper so the tests
    cannot drift from how ``isError()`` responses are classified.
    """

    is_modbus_error = staticmethod(ModbusTransportSession.is_modbus_error)

    def __init__(self, client: _ScriptedWriteClient) -> None:
        self._client = client

    @property
    def client(self) -> _ScriptedWriteClient:
        return self._client

    async def ensure_connection(self) -> _ScriptedWriteClient:
        return self._client


def _repository(result) -> tuple[ModbusRegisterRepository, _ScriptedWriteClient]:
    """Build the real repository on top of a scripted client boundary."""
    client = _ScriptedWriteClient(result)
    session = _SessionStub(client)
    return ModbusRegisterRepository(session), client


# --------------------------------------------------------------------------
# Select-register writes (reported failure: holding_9 / holding_68)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("register_name", "expected_address"),
    [
        ("holding_9", 9),  # Quiet mode operation
        ("holding_68", 68),  # Weather-dependent mode Heating Main
    ],
    ids=["holding_9", "holding_68"],
)
async def test_write_select_register_sends_raw_value_to_correct_address(
    register_name: str, expected_address: int
) -> None:
    """A select write must reach the device as FC06 at the documented address."""
    repository, client = _repository(_OkResponse())

    result = await repository.write_holding_register(register_name, 1)

    assert result is not None
    assert client.write_calls == [(expected_address, 1)]


async def test_write_negative_signed_register_converts_to_twos_complement() -> None:
    """Negative values for signed registers are sent as 16-bit two's complement."""
    repository, client = _repository(_OkResponse())

    await repository.write_holding_register("holding_54", -5)

    # -5 + 65536 = 65531 (INT16 signed, heating setpoint offset -10..10)
    assert client.write_calls == [(54, 65531)]


async def test_write_non_negative_signed_register_is_sent_unchanged() -> None:
    """Non-negative values must not be shifted by the signed conversion."""
    repository, client = _repository(_OkResponse())

    await repository.write_holding_register("holding_54", 5)

    assert client.write_calls == [(54, 5)]


# --------------------------------------------------------------------------
# Failure paths
# --------------------------------------------------------------------------


async def test_write_protocol_error_raises_device_exception() -> None:
    """A refused write must surface as ModbusDeviceException, not success."""
    repository, client = _repository(_ErrorResponse())

    with pytest.raises(ModbusDeviceException):
        await repository.write_holding_register("holding_9", 1)

    assert client.write_calls == [(9, 1)]


# --------------------------------------------------------------------------
# Register-config lookup used by the write path
# --------------------------------------------------------------------------


def test_get_register_config_resolves_default_holding_register_list() -> None:
    """Default lookup must resolve the restructured register constants."""
    register = get_register_config("holding_9")

    assert register is not None
    assert register.address == 9
    assert register.data_type is not None
    assert register.data_type.signed is True
