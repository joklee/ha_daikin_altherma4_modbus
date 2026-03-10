"""Register-repository layer for Modbus register access."""

import asyncio
import logging
import time
from typing import Any

from .const import MAX_MODBUS_ADDRESS, MIN_MODBUS_ADDRESS
from .exceptions import (
    ModbusConnectionException,
    ModbusDeviceException,
    ModbusReadException,
    ModbusTimeoutException,
    ModbusWriteException,
)
from .transport_session import ModbusTransportSession

_LOGGER = logging.getLogger(__name__)


def _validate_modbus_address(address: int, context: str = "address") -> int:
    """
    Validate and clamp Modbus address to valid range based on device documentation.

    Args:
        address: The address to validate
        context: Context description for error messages

    Returns:
        Validated address clamped to device-specific range (1-87)

    Raises:
        ValueError: If address is not a valid integer
    """
    if not isinstance(address, int):
        raise ValueError(
            f"Invalid {context}: must be integer, got {type(address).__name__}"
        )

    if address < MIN_MODBUS_ADDRESS or address > MAX_MODBUS_ADDRESS:
        _LOGGER.warning(
            f"Modbus {context} {address} is outside valid device range ({MIN_MODBUS_ADDRESS}-{MAX_MODBUS_ADDRESS}), clamping"
        )
        address = max(MIN_MODBUS_ADDRESS, min(MAX_MODBUS_ADDRESS, address))

    return address


_READ_EXCEPTIONS = (
    ModbusReadException,
    ModbusTimeoutException,
    ModbusDeviceException,
    ModbusConnectionException,
    asyncio.TimeoutError,
    OSError,
    ConnectionError,
)
_WRITE_EXCEPTIONS = (
    ModbusWriteException,
    ModbusTimeoutException,
    ModbusDeviceException,
    ModbusConnectionException,
    asyncio.TimeoutError,
    OSError,
    ConnectionError,
)


class ModbusRegisterRepository:
    """Reads and writes Modbus registers for configured blocks."""

    def __init__(self, session: ModbusTransportSession):
        self._session = session

    async def read_input_blocks(self) -> list[tuple[Any, int, int, int]]:
        """Read configured input-register blocks."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read input registers")
            return []

        blocks: list[tuple[Any, int, int, int]] = []

        # 🚀 OPTIMIZED: Single batch read for all input registers (21-87)
        # Before: 2 separate reads (21-53, 54-87)
        # After: 1 single read (21-87) = 50% faster!
        try:
            block_start = time.time()
            result = await client.read_input_registers(
                21, 67
            )  # 67 Register in einem Aufruf!
            _LOGGER.debug(
                "Optimized Input Register Block (21-87) read in %.3fs",
                time.time() - block_start,
            )

            if not self._session.is_modbus_error(result):
                blocks.append((result, 21, 87, 21))
                _LOGGER.debug(
                    "✅ Batch optimization successful: 67 registers in 1 read"
                )
            else:
                _LOGGER.error("Optimized Input Register Block read failed")
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read optimized Input Register Block: %s", err)

        return blocks

    async def read_discrete_inputs(self) -> Any | None:
        """Read discrete inputs with one reconnect retry."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read discrete inputs")
            return None

        try:
            read_start = time.time()
            result = await client.read_discrete_inputs(1, 26)
            _LOGGER.debug(
                "Discrete Inputs (30 bits) read in %.3fs", time.time() - read_start
            )

            if not self._session.is_modbus_error(result):
                return result

            self._log_unsupported_register_type(result, "discrete inputs")
            return None
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read Discrete Inputs: %s", err)
            return await self._retry_read_discrete_inputs()

    async def read_coils(self) -> Any | None:
        """Read coils with one reconnect retry."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read coils")
            return None

        try:
            read_start = time.time()
            result = await client.read_coils(1, 3)
            _LOGGER.debug("Coils (20 bits) read in %.3fs", time.time() - read_start)

            if not self._session.is_modbus_error(result):
                return result

            self._log_unsupported_register_type(result, "coils")
            return None
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read Coils: %s", err)
            return await self._retry_read_coils()

    async def read_holding_blocks(self) -> list[tuple[Any, int, int, int]]:
        """Read configured holding-register blocks."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read holding registers")
            return []

        data_blocks: list[tuple[Any, int, int, int]] = []

        # 🚀 OPTIMIZED: Single batch read for all holding registers (1-79)
        # Before: 3 separate reads (1-25, 26-50, 51-80) + 200ms delays
        # After: 1 single read (1-79) = 66% faster + no delays!
        try:
            block_start = time.time()
            result = await client.read_holding_registers(
                1, 79
            )  # 79 Register in einem Aufruf!
            _LOGGER.debug(
                "Optimized Holding Register Block (1-79) read in %.3fs",
                time.time() - block_start,
            )

            if not self._session.is_modbus_error(result):
                data_blocks.append((result, 1, 79, 1))
                _LOGGER.debug(
                    "✅ Batch optimization successful: 79 registers in 1 read"
                )
            else:
                _LOGGER.warning(
                    "Device does not support full holding register range (1-79)"
                )
                # Fallback: Try individual blocks if full range fails
                await self._fallback_holding_blocks(data_blocks)
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read optimized Holding Register Block: %s", err)
            # Fallback: Try individual blocks on error
            await self._fallback_holding_blocks(data_blocks)

        return data_blocks

    async def _fallback_holding_blocks(
        self, data_blocks: list[tuple[Any, int, int, int]]
    ) -> None:
        """Fallback to individual blocks if optimized batch fails."""
        blocks = [
            (1, 25, 1, 25, 1, "Block 1", False),
            (26, 25, 26, 50, 26, "Block 2", False),
            (51, 30, 51, 80, 51, "Block 3", True),
        ]

        _LOGGER.debug("Using fallback individual block reading")
        for start_addr, count, min_addr, max_addr, offset, name, optional in blocks:
            result = await self._read_holding_register_block(
                start_addr, count, min_addr, max_addr, offset, name, optional
            )
            if result is not None:
                data_blocks.append((result, min_addr, max_addr, offset))

    async def write_holding_register(self, register_name: str, value: int) -> Any:
        """Write a holding register by register name."""
        client = await self._session.ensure_connection()
        if client is None:
            error_msg = f"Cannot write holding register {register_name} - Modbus connection unavailable"
            _LOGGER.error(error_msg)
            raise ModbusConnectionException(error_msg)

        try:
            address = int(register_name.split("_")[1])
        except (ValueError, IndexError):
            error_msg = f"Invalid address name format: {register_name}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Validate and clamp address to valid Modbus range
        address = _validate_modbus_address(
            address, f"holding register address {register_name}"
        )

        try:
            result = await client.write_holding_register(address, value)
            if self._session.is_modbus_error(result):
                error_msg = f"Failed to write register {register_name} (address {address}) with value {value}: {result}"
                _LOGGER.error(error_msg)
                raise ModbusDeviceException(error_msg)

            _LOGGER.debug(
                "Successfully wrote register %s (address %s) with value %s",
                register_name,
                address,
                value,
            )
            return result
        except _WRITE_EXCEPTIONS:
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as err:
            error_msg = f"Unexpected exception writing register {register_name} (address {address}) with value {value}: {err}"
            _LOGGER.error(error_msg)
            raise ModbusWriteException(error_msg) from err

    async def write_coil_register(self, register_name: str, value: bool) -> Any:
        """Write a coil register by register name."""
        client = await self._session.ensure_connection()
        if client is None:
            error_msg = (
                f"Cannot write coil {register_name} - Modbus connection unavailable"
            )
            _LOGGER.error(error_msg)
            raise ModbusConnectionException(error_msg)

        if isinstance(register_name, str) and register_name.startswith("coil_"):
            try:
                address = int(register_name.split("_")[1])
            except (ValueError, IndexError):
                error_msg = f"Invalid address name format: {register_name}"
                _LOGGER.error(error_msg)
                raise ValueError(error_msg)
        elif isinstance(register_name, int):
            address = register_name
        else:
            error_msg = f"Invalid address format: {register_name}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Validate and clamp address to valid Modbus range
        address = _validate_modbus_address(address, f"coil address {register_name}")

        try:
            result = await client.write_coil_register(address, value)
            if self._session.is_modbus_error(result):
                error_msg = f"Failed to write coil {register_name} (address {address}) with value {value}: {result}"
                _LOGGER.error(error_msg)
                raise ModbusDeviceException(error_msg)

            _LOGGER.debug(
                "Successfully wrote coil %s (address %s) with value %s",
                register_name,
                address,
                value,
            )
            return result
        except _WRITE_EXCEPTIONS:
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as err:
            error_msg = f"Unexpected exception writing coil {register_name} (address {address}) with value {value}: {err}"
            _LOGGER.error(error_msg)
            raise ModbusWriteException(error_msg) from err

    async def read_single_holding_register(self, address: int) -> Any | None:
        """Read one holding register value."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read holding register")
            return None
        try:
            result = await client.read_holding_registers(address, 1)
            if self._session.is_modbus_error(result):
                _LOGGER.error("Failed to read holding register %s: %s", address, result)
                return None
            return result
        except _READ_EXCEPTIONS as err:
            _LOGGER.error("Exception reading holding register %s: %s", address, err)
            return None

    async def read_single_coil(self, address: int) -> Any | None:
        """Read one coil value."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read coil")
            return None
        try:
            result = await client.read_coils(address, 1)
            if self._session.is_modbus_error(result):
                _LOGGER.error("Failed to read coil %s: %s", address, result)
                return None
            return result
        except _READ_EXCEPTIONS as err:
            _LOGGER.error("Exception reading coil %s: %s", address, err)
            return None

    async def _retry_read_discrete_inputs(self) -> Any | None:
        """Reconnect and retry discrete inputs once."""
        try:
            _LOGGER.info(
                "Attempting to re-establish connection and retry discrete inputs"
            )
            client = await self._session.reconnect_with_new_client()
            if client is None:
                return None

            result = await client.read_discrete_inputs(1, 26)
            if not self._session.is_modbus_error(result):
                _LOGGER.info("Successfully retried discrete inputs after reconnection")
                return result

            _LOGGER.warning(
                "Discrete inputs retry also failed - device may not support this register type: %s",
                result,
            )
            return None
        except _READ_EXCEPTIONS as retry_err:
            _LOGGER.warning("Retry attempt for discrete inputs failed: %s", retry_err)
            return None

    async def _retry_read_coils(self) -> Any | None:
        """Reconnect and retry coils once."""
        try:
            _LOGGER.info("Attempting to re-establish connection and retry coils")
            client = await self._session.reconnect_with_new_client()
            if client is None:
                return None

            result = await client.read_coils(1, 3)
            if not self._session.is_modbus_error(result):
                _LOGGER.info("Successfully retried coils after reconnection")
                return result

            _LOGGER.warning(
                "Coils retry also failed - device may not support this register type: %s",
                result,
            )
            return None
        except _READ_EXCEPTIONS as retry_err:
            _LOGGER.warning("Retry attempt for coils failed: %s", retry_err)
            return None

    async def _read_holding_register_block(
        self,
        start_address: int,
        count: int,
        min_address: int,
        max_address: int,
        offset: int,
        block_name: str,
        is_optional: bool,
    ) -> Any | None:
        """Read one holding-register block with reconnect retry."""
        client = self._session.client
        if client is None:
            return None

        try:
            block_start = time.time()
            result = await client.read_holding_registers(start_address, count)
            _LOGGER.debug(
                "Holding Register %s (%s registers) read in %.3fs",
                block_name,
                count,
                time.time() - block_start,
            )

            if not self._session.is_modbus_error(result):
                return result

            if is_optional:
                _LOGGER.warning(
                    "Device does not support holding register %s (addresses %s-%s): %s",
                    block_name,
                    min_address,
                    max_address,
                    result,
                )
                _LOGGER.info(
                    "Skipping holding register %s - device may not support these address ranges",
                    block_name,
                )
            else:
                _LOGGER.error("Holding Register %s read failed: %s", block_name, result)
            return None
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read Holding Register %s: %s", block_name, err)
            return await self._retry_holding_block(
                start_address,
                count,
                min_address,
                max_address,
                offset,
                block_name,
                is_optional,
            )

    async def _retry_holding_block(
        self,
        start_address: int,
        count: int,
        min_address: int,
        max_address: int,
        offset: int,
        block_name: str,
        is_optional: bool,
    ) -> Any | None:
        """Retry one holding block after reconnect."""
        del offset  # offset is part of repository contract, not needed for retry read

        try:
            _LOGGER.info(
                "Attempting to re-establish connection and retry holding register %s",
                block_name,
            )
            client = await self._session.reconnect_with_new_client()
            if client is None:
                return None

            retry_result = await client.read_holding_registers(start_address, count)
            if not self._session.is_modbus_error(retry_result):
                _LOGGER.info(
                    "Successfully retried holding register %s after reconnection",
                    block_name,
                )
                return retry_result

            if is_optional:
                _LOGGER.warning(
                    "Holding Register %s retry also failed - device may not support these addresses: %s",
                    block_name,
                    retry_result,
                )
            else:
                _LOGGER.warning(
                    "Holding Register %s retry also failed: %s",
                    block_name,
                    retry_result,
                )
            return None
        except _READ_EXCEPTIONS as retry_err:
            _LOGGER.warning(
                "Retry attempt for Holding Register %s failed: %s",
                block_name,
                retry_err,
            )
            return None

    @staticmethod
    def _log_unsupported_register_type(result: Any, register_type: str) -> None:
        """Log device support diagnostics for register types."""
        error_msg = str(result)
        if "exception_code=2" in error_msg:
            _LOGGER.warning(
                "Device does not support %s (Illegal data address)", register_type
            )
        elif "exception_code=1" in error_msg:
            _LOGGER.warning(
                "Device does not support %s (Illegal function)", register_type
            )
        else:
            _LOGGER.warning(
                "Device does not support %s or read failed: %s", register_type, result
            )
        _LOGGER.info(
            "Skipping %s - device may not support this register type", register_type
        )
