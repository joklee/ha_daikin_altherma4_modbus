"""Real Modbus client wrapper."""

import asyncio
import logging

import pymodbus.exceptions
from pymodbus.client import AsyncModbusTcpClient

from .client_interface import ModbusClientInterface
from .exceptions import (
    ModbusDeviceException,
    ModbusReadException,
    ModbusTimeoutException,
    ModbusWriteException,
)

_LOGGER = logging.getLogger(__name__)

# Global cache for AsyncModbusTcpClient instances and locks
_client_cache = {}
_client_locks = {}
_cache_lock = asyncio.Lock()  # Global lock for cache operations


class OneBasedModbusResponse:
    """Wrapper for Modbus responses to provide 1-based indexing."""

    def __init__(self, original_response, start_address: int, is_bits: bool = False):
        self.original_response = original_response
        self.start_address = start_address  # The starting address that was requested
        self.is_bits = is_bits

    @property
    def registers(self):
        """Return 1-based register array."""
        if hasattr(self.original_response, "registers"):
            # Size dynamically by requested start + returned payload length.
            payload_len = len(self.original_response.registers)
            max_possible_address = self.start_address + payload_len - 1
            result = [32766] * (max_possible_address + 1)

            # Place returned registers at the correct positions
            for i, value in enumerate(self.original_response.registers):
                result[self.start_address + i] = value

            _LOGGER.debug(
                f"OneBasedModbusResponse: start_address={self.start_address}, len={len(self.original_response.registers)}, result_len={len(result)}"
            )
            return result
        return [32766]  # Default with dummy element

    @property
    def bits(self):
        """Return 1-based bit array."""
        if hasattr(self.original_response, "bits"):
            # Size dynamically by requested start + returned payload length.
            payload_len = len(self.original_response.bits)
            max_possible_address = self.start_address + payload_len - 1
            result = [False] * (max_possible_address + 1)

            # Place returned bits at the correct positions
            for i, value in enumerate(self.original_response.bits):
                result[self.start_address + i] = value

            return result
        return [False]  # Default with dummy element

    def is_error(self):
        """Check if the original response is an error."""
        return (
            self.original_response.isError()
            if hasattr(self.original_response, "isError")
            else False
        )


class RealModbusTcpClient(ModbusClientInterface):
    """Wrapper for the real AsyncModbusTcpClient to implement ModbusClientInterface with caching and lazy reconnect."""

    def __init__(self, host: str, port: int = 502, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._reconnect_needed = False
        self._client = None
        self._lock = None

    async def _initialize_client(self) -> None:
        """Initialize the client with thread-safe cache access."""
        if self._client is not None:
            return  # Already initialized

        # Create cache key from host:port
        cache_key = f"{self.host}:{self.port}"

        # Use global lock to prevent race conditions during cache access
        async with _cache_lock:
            if cache_key in _client_cache:
                self._client = _client_cache[cache_key]
                self._lock = _client_locks[cache_key]
                _LOGGER.info(f"Using cached AsyncModbusTcpClient for {cache_key}")
            else:
                # Create new client and cache it
                self._client = AsyncModbusTcpClient(
                    self.host, port=self.port, timeout=self.timeout, retries=1
                )
                self._lock = asyncio.Lock()
                _client_cache[cache_key] = self._client
                _client_locks[cache_key] = self._lock
                _LOGGER.info(
                    f"Created and cached new AsyncModbusTcpClient for {cache_key}"
                )

    @classmethod
    async def create(
        cls, host: str, port: int = 502, timeout: int = 10
    ) -> "RealModbusTcpClient":
        """Factory method to create and initialize a RealModbusTcpClient instance."""
        instance = cls(host, port, timeout)
        await instance._initialize_client()
        return instance

    @property
    def connected(self) -> bool:
        """Check if client is connected."""
        if self._client is None:
            return False
        return self._client.connected

    async def connect(self) -> None:
        """Connect to Modbus server with lazy reconnect."""
        await self._ensure_initialized()
        if self._reconnect_needed or not self._client.connected:
            _LOGGER.info(f"Lazy reconnect: connecting to {self.host}:{self.port}")
            await self._client.connect()
            self._reconnect_needed = False
        else:
            _LOGGER.debug(
                f"Already connected to {self.host}:{self.port}, skipping connect"
            )

    async def disconnect(self) -> None:
        """Disconnect from Modbus server."""
        await self._ensure_initialized()
        if self._client.connected:
            _LOGGER.info(f"Disconnecting from {self.host}:{self.port}")
            self._client.close()
            self._reconnect_needed = True

    async def read_input_registers(self, address: int, count: int):
        """Read input registers."""
        await self._ensure_initialized()
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.debug(
                f"Reading input registers from address {address} with count {count}"
            )
            try:
                original_response = await self._client.read_input_registers(
                    address - 1, count=count
                )
                if self._is_modbus_error(original_response):
                    raise ModbusDeviceException(
                        f"Device error reading input registers at {address}"
                    )
                return OneBasedModbusResponse(original_response, address, is_bits=False)
            except pymodbus.exceptions.ModbusIOException as e:
                raise ModbusReadException(
                    f"I/O error reading input registers at {address}", e
                )
            except asyncio.TimeoutError as e:
                raise ModbusTimeoutException(
                    f"Timeout reading input registers at {address}", e
                )
            except pymodbus.exceptions.ModbusException as e:
                raise ModbusReadException(
                    f"Modbus error reading input registers at {address}", e
                )

    async def read_holding_registers(self, address: int, count: int):
        """Read holding registers."""
        await self._ensure_initialized()
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.debug(
                f"Reading holding registers from address {address} with count {count}"
            )
            try:
                original_response = await self._client.read_holding_registers(
                    address - 1, count=count
                )
                if self._is_modbus_error(original_response):
                    raise ModbusDeviceException(
                        f"Device error reading holding registers at {address}"
                    )
                return OneBasedModbusResponse(original_response, address, is_bits=False)
            except pymodbus.exceptions.ModbusIOException as e:
                raise ModbusReadException(
                    f"I/O error reading holding registers at {address}", e
                )
            except asyncio.TimeoutError as e:
                raise ModbusTimeoutException(
                    f"Timeout reading holding registers at {address}", e
                )
            except pymodbus.exceptions.ModbusException as e:
                raise ModbusReadException(
                    f"Modbus error reading holding registers at {address}", e
                )

    async def read_discrete_inputs(self, address: int, count: int):
        """Read discrete inputs."""
        await self._ensure_initialized()
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.debug(
                f"Reading discrete inputs from address {address} with count {count}"
            )
            try:
                original_response = await self._client.read_discrete_inputs(
                    address - 1, count=count
                )
                if self._is_modbus_error(original_response):
                    raise ModbusDeviceException(
                        f"Device error reading discrete inputs at {address}"
                    )
                return OneBasedModbusResponse(original_response, address, is_bits=True)
            except pymodbus.exceptions.ModbusIOException as e:
                raise ModbusReadException(
                    f"I/O error reading discrete inputs at {address}", e
                )
            except asyncio.TimeoutError as e:
                raise ModbusTimeoutException(
                    f"Timeout reading discrete inputs at {address}", e
                )
            except pymodbus.exceptions.ModbusException as e:
                raise ModbusReadException(
                    f"Modbus error reading discrete inputs at {address}", e
                )

    async def read_coils(self, address: int, count: int):
        """Read coils."""
        await self._ensure_initialized()
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.debug(f"Reading coils from address {address} with count {count}")
            try:
                original_response = await self._client.read_coils(
                    address - 1, count=count
                )
                if self._is_modbus_error(original_response):
                    raise ModbusDeviceException(
                        f"Device error reading coils at {address}"
                    )
                return OneBasedModbusResponse(original_response, address, is_bits=True)
            except pymodbus.exceptions.ModbusIOException as e:
                raise ModbusReadException(f"I/O error reading coils at {address}", e)
            except asyncio.TimeoutError as e:
                raise ModbusTimeoutException(f"Timeout reading coils at {address}", e)
            except pymodbus.exceptions.ModbusException as e:
                raise ModbusReadException(f"Modbus error reading coils at {address}", e)

    async def write_holding_register(self, address: int, value: int):
        await self._ensure_initialized()
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.debug(f"Writing to holding register {address} with value {value}")
            try:
                result = await self._client.write_register(address - 1, value)
                if self._is_modbus_error(result):
                    raise ModbusDeviceException(
                        f"Device error writing holding register {address}"
                    )
                return result
            except pymodbus.exceptions.ModbusIOException as e:
                raise ModbusWriteException(
                    f"I/O error writing holding register {address}", e
                )
            except asyncio.TimeoutError as e:
                raise ModbusTimeoutException(
                    f"Timeout writing holding register {address}", e
                )
            except pymodbus.exceptions.ModbusException as e:
                raise ModbusWriteException(
                    f"Modbus error writing holding register {address}", e
                )

    async def write_coil_register(self, address: int, value: bool):
        await self._ensure_initialized()
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.debug(f"Writing to coil register {address} with value {value}")
            try:
                result = await self._client.write_coil(address - 1, value)
                if self._is_modbus_error(result):
                    raise ModbusDeviceException(f"Device error writing coil {address}")
                return result
            except pymodbus.exceptions.ModbusIOException as e:
                raise ModbusWriteException(f"I/O error writing coil {address}", e)
            except asyncio.TimeoutError as e:
                raise ModbusTimeoutException(f"Timeout writing coil {address}", e)
            except pymodbus.exceptions.ModbusException as e:
                raise ModbusWriteException(f"Modbus error writing coil {address}", e)

    async def _ensure_initialized(self) -> None:
        """Ensure the client is initialized before use."""
        if self._client is None:
            await self._initialize_client()

    async def _ensure_connection(self) -> None:
        """Ensure connection is active before operations."""
        await self._ensure_initialized()
        if not self._client.connected or self._reconnect_needed:
            _LOGGER.info(
                f"Connection lost, attempting lazy reconnect to {self.host}:{self.port}"
            )
            await self.connect()

    @staticmethod
    def _is_modbus_error(response) -> object | bool:
        """Check if Modbus response indicates an error, compatible with both mock and real clients."""
        # Try isError() first (pymodbus standard)
        if hasattr(response, "isError") and callable(response.isError):
            return response.isError()
        # Fallback to checking for error code/function code
        if hasattr(response, "function_code") and hasattr(response, "exception_code"):
            return response.function_code >= 0x80
        return False

    @classmethod
    def clear_cache(cls):
        """Clear the client cache (useful for testing or reconnection)."""
        global _client_cache, _client_locks
        _client_cache.clear()
        _client_locks.clear()
        _LOGGER.debug("AsyncModbusTcpClient cache cleared")

    @classmethod
    async def safe_clear_cache(cls):
        """Thread-safe version of clear_cache."""
        async with _cache_lock:
            cls.clear_cache()

    @classmethod
    async def async_close_cached_client(cls, host: str, port: int = 502) -> None:
        """Close and remove a specific cached client."""
        global _client_cache, _client_locks
        cache_key = f"{host}:{port}"

        async with _cache_lock:
            client = _client_cache.get(cache_key)

            if client is None:
                return

            try:
                if getattr(client, "connected", False):
                    client.close()
            except Exception as err:
                _LOGGER.debug("Failed closing cached client %s: %s", cache_key, err)
            finally:
                _client_cache.pop(cache_key, None)
                _client_locks.pop(cache_key, None)
                _LOGGER.debug("Removed cached AsyncModbusTcpClient for %s", cache_key)
