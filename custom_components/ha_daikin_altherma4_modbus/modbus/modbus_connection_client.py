"""Thin facade over ``modbus_connection.ModbusUnit``.

Phase 2 of the ``modbus-connection`` migration. This facade adapts the
``modbus_connection`` transport to the integration's
:class:`ModbusClientInterface` contract:

- Daikin registers are 1-based (21-87, 1-80, ...); the raw unit API is
  0-based, so every call translates ``address - 1`` (hard contract from the
  Phase 0 spike A2).
- Reads return flat ``list`` values; special protocol values
  (32765/32766/32767) pass through untouched.
- Failures raise the ``ModbusError`` hierarchy; this facade maps them onto
  the integration's own exception types at this single boundary.
- Writes delegate to ``write_register`` / ``write_coil`` (FC06/FC05).

The production path still uses the legacy ``RealModbusTcpClient`` until the
Phase 5 cutover; this facade is the tested migration target.
"""

from __future__ import annotations

import logging
from typing import Any

from ..core.exceptions import (
    ModbusConnectionException,
    ModbusInvalidAddressException,
    ModbusReadException,
    ModbusTimeoutException,
    ModbusWriteException,
)
from .client_interface import ModbusClientInterface

try:
    from modbus_connection import ModbusConnection
    from modbus_connection.exceptions import (
        IllegalDataAddressError,
        ModbusConnectionError,
        ModbusError,
        ModbusTimeoutError,
    )
except ImportError:  # pragma: no cover - modbus-connection not installed
    ModbusConnection = None  # type: ignore[assignment,misc]
    IllegalDataAddressError = None  # type: ignore[assignment,misc]
    ModbusConnectionError = None  # type: ignore[assignment,misc]
    ModbusError = None  # type: ignore[assignment,misc]
    ModbusTimeoutError = None  # type: ignore[assignment,misc]

_LOGGER = logging.getLogger(__name__)


class ModbusConnectionClient(ModbusClientInterface):
    """Adapt a shared ``ModbusConnection`` / ``ModbusUnit`` to the interface."""

    def __init__(self, connection: ModbusConnection, unit_id: int = 1) -> None:
        self._connection = connection
        self._unit_id = unit_id
        self._unit: Any = None

    @property
    def connected(self) -> bool:
        """Check if the underlying connection is connected."""
        return bool(self._connection.connected)

    async def connect(self) -> None:
        """Connect to the Modbus server."""
        await self._connection.connect()

    async def disconnect(self) -> None:
        """Disconnect from the Modbus server."""
        await self._connection.disconnect()

    async def read_input_registers(self, address: int, count: int) -> Any:
        """Read input registers at 1-based address."""
        unit = await self._get_unit()
        try:
            return await unit.read_input_registers(address - 1, count)
        except ModbusError as err:
            self._raise_translated(err, read=True, address=address)

    async def read_holding_registers(self, address: int, count: int) -> Any:
        """Read holding registers at 1-based address."""
        unit = await self._get_unit()
        try:
            return await unit.read_holding_registers(address - 1, count)
        except ModbusError as err:
            self._raise_translated(err, read=True, address=address)

    async def read_discrete_inputs(self, address: int, count: int) -> Any:
        """Read discrete inputs at 1-based address."""
        unit = await self._get_unit()
        try:
            return await unit.read_discrete_inputs(address - 1, count)
        except ModbusError as err:
            self._raise_translated(err, read=True, address=address)

    async def read_coils(self, address: int, count: int) -> Any:
        """Read coils at 1-based address."""
        unit = await self._get_unit()
        try:
            return await unit.read_coils(address - 1, count)
        except ModbusError as err:
            self._raise_translated(err, read=True, address=address)

    async def write_holding_register(self, address: int, value: int) -> Any:
        """Write a holding register at 1-based address (FC06)."""
        unit = await self._get_unit()
        try:
            return await unit.write_register(address - 1, value)
        except ModbusError as err:
            self._raise_translated(err, read=False, address=address)

    async def write_coil_register(self, address: int, value: bool) -> Any:
        """Write a coil at 1-based address (FC05)."""
        unit = await self._get_unit()
        try:
            return await unit.write_coil(address - 1, value)
        except ModbusError as err:
            self._raise_translated(err, read=False, address=address)

    async def _get_unit(self) -> Any:
        """Return the lazily-cached unit for this connection and unit id."""
        if self._unit is None:
            self._unit = self._connection.for_unit(self._unit_id)
        return self._unit

    def _raise_translated(self, err: Exception, *, read: bool, address: int) -> None:
        """Raise the integration exception matching a ModbusError.

        The ``original_error`` is attached so the root cause stays inspectable.
        """
        if ModbusTimeoutError is not None and isinstance(err, ModbusTimeoutError):
            raise ModbusTimeoutException(
                f"Timeout on {'read' if read else 'write'} at {address}", err
            ) from err
        if ModbusConnectionError is not None and isinstance(err, ModbusConnectionError):
            raise ModbusConnectionException(
                f"Connection error on {'read' if read else 'write'} at {address}",
                err,
            ) from err
        if IllegalDataAddressError is not None and isinstance(
            err, IllegalDataAddressError
        ):
            raise ModbusInvalidAddressException(
                f"Invalid address {address}", err
            ) from err
        # All other ModbusErrors map to the read/write exception by direction.
        if read:
            raise ModbusReadException(f"Read error at {address}", err) from err
        raise ModbusWriteException(f"Write error at {address}", err) from err
