"""Thin facade over ``modbus_connection.ModbusUnit``.

This facade adapts the ``modbus_connection`` transport to the integration's
:class:`ModbusClientInterface` contract and is the production default
(obtained via ``async_get_ha_unit`` / the temporary-unit probe):

- Daikin registers are 1-based (21-87, 1-80, ...); the raw unit API is
  0-based, so every call translates ``address - 1`` (hard contract from the
  Phase 0 spike A2).
- Reads return flat ``list`` values; special protocol values
  (32765/32766/32767) pass through untouched.
- Failures raise the ``ModbusError`` hierarchy; this facade maps them onto
  the integration's own exception types at this single boundary.
- Writes delegate to ``write_register`` / ``write_coil`` (FC06/FC05).
"""

from __future__ import annotations

import logging
import time
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

# Single translation boundary (Phase 4): every ``ModbusError`` from the unit
# is mapped onto the integration hierarchy in ``_raise_translated``. Empty
# when ``modbus-connection`` is not installed so the ``except`` clause stays
# valid (it then never matches).
_MODBUS_ERROR_TYPES: tuple[type, ...] = (
    (ModbusError,) if isinstance(ModbusError, type) else ()
)


class ModbusConnectionClient(ModbusClientInterface):
    """Adapt a shared ``ModbusConnection`` / ``ModbusUnit`` to the interface.

    Can be constructed either from a ``ModbusConnection`` plus a ``unit_id``
    (the unit is then fetched lazily via ``connection.for_unit``) or directly
    from a ``ModbusUnit`` handed back by HA's ``async_get_unit``.
    """

    def __init__(
        self,
        connection: ModbusConnection | None = None,
        unit_id: int = 1,
        unit: Any | None = None,
    ) -> None:
        self._connection = connection
        self._unit_id = unit_id
        self._unit = unit
        # Epoch timestamps of the last successful read/write through this
        # facade. The unit itself holds no state, so consumers (connection
        # diagnostic sensors) read the history here instead.
        self.last_read_at: float | None = None
        self.last_write_at: float | None = None
        # Error counters by direction and category, plus the newest failure.
        # Neither the unit nor HA's shared component expose diagnostics, so
        # the facade (the single translation boundary) counts them itself.
        self.error_counts: dict[str, int] = {
            f"{direction}_{category}": 0
            for direction in ("read", "write")
            for category in ("timeout", "connection", "invalid_address", "other")
        }
        self.last_error_at: float | None = None
        self.last_error: str | None = None

    @property
    def connected(self) -> bool:
        """Check if the underlying connection is connected."""
        if self._unit is not None:
            return bool(getattr(self._unit, "connected", False))
        if self._connection is not None:
            return bool(self._connection.connected)
        return False

    async def connect(self) -> None:
        """Connect to the Modbus server.

        A unit handed back by ``async_get_unit`` is lazy and managed by HA, so
        there is nothing to connect; only an owned ``connection`` connects.
        """
        if self._connection is not None:
            await self._connection.connect()

    async def disconnect(self) -> None:
        """Disconnect from the Modbus server.

        A unit handed back by ``async_get_unit`` is owned and shared by HA's
        ``modbus`` component: dropping its link is a lifecycle decision of
        that component, so a facade wrapping a bare unit is a no-op here.
        Only an owned ``connection`` (built directly in tests/standalone)
        disconnects.
        """
        if self._unit is not None:
            return
        if self._connection is not None:
            await self._connection.disconnect()

    async def read_input_registers(self, address: int, count: int) -> Any:
        """Read input registers at 1-based address."""
        unit = await self._get_unit()
        try:
            result = await unit.read_input_registers(address - 1, count)
            self.last_read_at = time.time()
            return result
        except _MODBUS_ERROR_TYPES as err:
            self._record_error(err, read=True, address=address)

    async def read_holding_registers(self, address: int, count: int) -> Any:
        """Read holding registers at 1-based address."""
        unit = await self._get_unit()
        try:
            result = await unit.read_holding_registers(address - 1, count)
            self.last_read_at = time.time()
            return result
        except _MODBUS_ERROR_TYPES as err:
            self._record_error(err, read=True, address=address)

    async def read_discrete_inputs(self, address: int, count: int) -> Any:
        """Read discrete inputs at 1-based address."""
        unit = await self._get_unit()
        try:
            result = await unit.read_discrete_inputs(address - 1, count)
            self.last_read_at = time.time()
            return result
        except _MODBUS_ERROR_TYPES as err:
            self._record_error(err, read=True, address=address)

    async def read_coils(self, address: int, count: int) -> Any:
        """Read coils at 1-based address."""
        unit = await self._get_unit()
        try:
            result = await unit.read_coils(address - 1, count)
            self.last_read_at = time.time()
            return result
        except _MODBUS_ERROR_TYPES as err:
            self._record_error(err, read=True, address=address)

    async def write_holding_register(self, address: int, value: int) -> Any:
        """Write a holding register at 1-based address (FC06)."""
        unit = await self._get_unit()
        try:
            result = await unit.write_register(address - 1, value)
            self.last_write_at = time.time()
            return result
        except _MODBUS_ERROR_TYPES as err:
            self._record_error(err, read=False, address=address)

    async def write_coil_register(self, address: int, value: bool) -> Any:
        """Write a coil at 1-based address (FC05)."""
        unit = await self._get_unit()
        try:
            result = await unit.write_coil(address - 1, value)
            self.last_write_at = time.time()
            return result
        except _MODBUS_ERROR_TYPES as err:
            self._record_error(err, read=False, address=address)

    async def _get_unit(self) -> Any:
        """Return the unit, fetching it lazily if built from a connection."""
        if self._unit is None and self._connection is not None:
            self._unit = self._connection.for_unit(self._unit_id)
        return self._unit

    @staticmethod
    def _classify_error(err: Exception) -> str:
        """Map a ``ModbusError`` onto a counter category."""
        if ModbusTimeoutError is not None and isinstance(err, ModbusTimeoutError):
            return "timeout"
        if ModbusConnectionError is not None and isinstance(err, ModbusConnectionError):
            return "connection"
        if IllegalDataAddressError is not None and isinstance(
            err, IllegalDataAddressError
        ):
            return "invalid_address"
        return "other"

    def _record_error(self, err: Exception, *, read: bool, address: int) -> None:
        """Count a failure, remember it, and raise the translated exception."""
        category = self._classify_error(err)
        direction = "read" if read else "write"
        self.error_counts[f"{direction}_{category}"] += 1
        self.last_error_at = time.time()
        self.last_error = f"{direction} at {address}: {type(err).__name__}: {err}"
        self._raise_translated(err, read=read, address=address)

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
