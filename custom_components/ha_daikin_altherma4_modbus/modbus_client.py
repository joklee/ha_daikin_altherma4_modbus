"""Real Modbus client wrapper."""

import logging
import asyncio
from pymodbus.client import AsyncModbusTcpClient
from .client_interface import ModbusClientInterface

_LOGGER = logging.getLogger(__name__)

# Global cache for AsyncModbusTcpClient instances and locks
_client_cache = {}
_client_locks = {}


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
            # Create array large enough for all possible addresses (1-1000 as safe upper bound)
            max_possible_address = 1000  # Safe upper bound for all possible addresses
            result = [32766] * (
                max_possible_address + 1
            )  # +1 for 1-based indexing (dummy at index 0)

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
            # Create array large enough for all possible addresses (1-1000 as safe upper bound)
            max_possible_address = 1000  # Safe upper bound for all possible addresses
            result = [False] * (
                max_possible_address + 1
            )  # +1 for 1-based indexing (dummy at index 0)

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

        # Create cache key from host:port
        cache_key = f"{host}:{port}"

        # Return cached client if exists
        if cache_key in _client_cache:
            self._client = _client_cache[cache_key]
            self._lock = _client_locks[cache_key]
            _LOGGER.info(f"Using cached AsyncModbusTcpClient for {cache_key}")
        else:
            # Create new client and cache it
            self._client = AsyncModbusTcpClient(
                host, port=port, timeout=timeout, retries=1
            )
            self._lock = asyncio.Lock()
            _client_cache[cache_key] = self._client
            _client_locks[cache_key] = self._lock
            _LOGGER.info(f"Created and cached new AsyncModbusTcpClient for {cache_key}")

    @property
    def connected(self) -> bool:
        """Check if client is connected."""
        return self._client.connected

    async def connect(self) -> None:
        """Connect to Modbus server with lazy reconnect."""
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
        if self._client.connected:
            _LOGGER.info(f"Disconnecting from {self.host}:{self.port}")
            self._client.close()
            self._reconnect_needed = True

    async def read_input_registers(self, address: int, count: int):
        """Read input registers."""
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.warning(
                f"Reading input registers from address {address} with count {count}"
            )
            original_response = await self._client.read_input_registers(
                address - 1, count=count
            )
            return OneBasedModbusResponse(original_response, address, is_bits=False)

    async def read_holding_registers(self, address: int, count: int):
        """Read holding registers."""
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.warning(
                f"Reading holding registers from address {address} with count {count}"
            )
            original_response = await self._client.read_holding_registers(
                address - 1, count=count
            )
            return OneBasedModbusResponse(original_response, address, is_bits=False)

    async def read_discrete_inputs(self, address: int, count: int):
        """Read discrete inputs."""
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.warning(
                f"Reading discrete inputs from address {address} with count {count}"
            )
            original_response = await self._client.read_discrete_inputs(
                address - 1, count=count
            )
            return OneBasedModbusResponse(original_response, address, is_bits=True)

    async def read_coils(self, address: int, count: int):
        """Read coils."""
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.warning(f"Reading coils from address {address} with count {count}")
            original_response = await self._client.read_coils(address - 1, count=count)
            return OneBasedModbusResponse(original_response, address, is_bits=True)

    async def write_holding_register(self, address: int, value: int):
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.info(f"Writing to holding register {address} with value {value}")
            return await self._client.write_register(address - 1, value)

    async def write_coil_register(self, address: int, value: bool):
        async with self._lock:
            await self._ensure_connection()
            _LOGGER.info(f"Writing to coil register {address} with value {value}")
            return await self._client.write_coil(address - 1, value)

    async def _ensure_connection(self) -> None:
        """Ensure connection is active before operations."""
        if not self._client.connected or self._reconnect_needed:
            _LOGGER.info(
                f"Connection lost, attempting lazy reconnect to {self.host}:{self.port}"
            )
            await self.connect()

    @classmethod
    def clear_cache(cls):
        """Clear the client cache (useful for testing or reconnection)."""
        global _client_cache
        _client_cache.clear()
        _LOGGER.debug("AsyncModbusTcpClient cache cleared")
