"""Fake Modbus client implementations for testing."""

import asyncio


class FakeModbusResponse:
    """Fake Modbus response for testing.

    This class provides a realistic mock of Modbus response objects,
    supporting both register and bit operations with 1-based indexing,
    matching the interface of MockModbusResponse from mock_client.py.
    """

    def __init__(self, data: list, address: int, count: int, is_bits: bool = False):
        """Initialize fake Modbus response.

        Args:
            data: List of register values or bit values
            address: Starting address (1-based)
            count: Number of registers/bits to expose
            is_bits: Whether this response contains bit values
        """
        self.is_bits = is_bits
        self._error = False
        self._count = count

        if is_bits:
            # For discrete inputs and coils - create 1-based array
            max_index = max(address + count, len(data)) + 1
            self.bits = [False] * max_index  # Index 0 is dummy
            for i in range(count):
                if address + i < len(data):
                    self.bits[address + i] = data[address + i]
                else:
                    self.bits[address + i] = False
        else:
            # For input and holding registers - create 1-based array
            max_index = max(address + count, len(data)) + 1
            self.registers = [32766] * max_index  # Index 0 is dummy
            for i in range(count):
                if address + i < len(data):
                    self.registers[address + i] = data[address + i]
                else:
                    self.registers[address + i] = 32766  # Unavailable

    def is_error(self) -> bool:
        """Return error status."""
        return self._error

    def isError(self) -> bool:
        """Return error status (alias for compatibility)."""
        return self._error

    def __len__(self) -> int:
        """Return the number of registers/bits in this response."""
        return self._count


class FakeModbusClient:
    """Centralized fake Modbus client for testing.

    This class provides a realistic mock of AsyncModbusTcpClient behavior
    for testing purposes, eliminating the need for scattered MagicMock
    configurations across test files.

    The timing_mode parameter allows performance tests to control timing:
    - 'normal': Default timing (1ms per operation)
    - 'fast': Minimal timing for benchmarks (0.1ms per operation)
    - 'realistic': Realistic network timing (10ms + variable)
    """

    # Class-level cache for demo data to avoid regenerating per instance
    _class_demo_data = None

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 502,
        timeout: int = 10,
        connected: bool = False,
    ):
        """Initialize fake Modbus client.

        Args:
            host: Mock host address
            port: Mock port
            timeout: Mock timeout
            connected: Initial connection state
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = connected
        self._connection_count = 0
        self._operation_count = 0
        self._read_operations = []
        self._write_operations = []
        self._registers = {}
        self._coils = {}
        self._discrete_inputs = {}
        self._holding_registers = {}

        # Mock-compatible call tracking
        self._connect_calls = []
        self._close_calls = []
        self._read_input_registers_calls = []
        self._read_holding_registers_calls = []
        self._read_discrete_inputs_calls = []
        self._read_coils_calls = []
        self._write_register_calls = []
        self._write_coil_calls = []

        # Custom return values for testing
        self._custom_responses = {}

        # Demo data for coverage tests compatibility (lazy-loaded)
        self._demo_data = None
        self._demo_data_loaded = False

    async def connect(self):
        """Simulate connection."""
        self.connected = True
        self._connection_count += 1
        self._connect_calls.append(())

    def close(self):
        """Simulate connection close."""
        self.connected = False
        self._close_calls.append(())

    async def disconnect(self):
        """Simulate disconnection (compatible with MockModbusTcpClient)."""
        self.connected = False
        self._close_calls.append(())

    async def read_input_registers(self, address: int, count: int, **kwargs):
        """Simulate reading input registers.

        Args:
            address: Register address (1-based)
            count: Number of registers to read
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            Mock response with registers
        """
        self._read_input_registers_calls.append((address, count, kwargs))

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self._read_operations.append(f"read_input_registers({address}, {count})")

        # Use custom register values if set, otherwise fall back to demo data
        custom_registers = self._registers.get("input", {}).get(address)
        if custom_registers is not None:
            # Build a full-length list with custom values at the correct address
            registers = list(self.demo_data.get("input_registers", []))
            for i, val in enumerate(custom_registers):
                if address + i < len(registers):
                    registers[address + i] = val
        else:
            # Pass the full register list (FakeModbusResponse handles address lookup)
            registers = self.demo_data.get("input_registers", [])

        return FakeModbusResponse(registers, address, count)

    async def read_holding_registers(self, address: int, count: int, **kwargs):
        """Simulate reading holding registers.

        Args:
            address: Register address (1-based)
            count: Number of registers to read
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            Mock response with registers
        """
        self._read_holding_registers_calls.append((address, count, kwargs))

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self._read_operations.append(f"read_holding_registers({address}, {count})")

        custom_registers = self._holding_registers.get(address)
        if custom_registers is not None:
            # Build a full-length list with custom values at the correct address
            registers = list(self.demo_data.get("holding_registers", []))
            for i, val in enumerate(custom_registers):
                if address + i < len(registers):
                    registers[address + i] = val
        else:
            # Pass the full register list (FakeModbusResponse handles address lookup)
            registers = self.demo_data.get("holding_registers", [])

        return FakeModbusResponse(registers, address, count)

    async def read_discrete_inputs(self, address: int, count: int, **kwargs):
        """Simulate reading discrete inputs.

        Args:
            address: Input address (1-based)
            count: Number of inputs to read
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            Mock response with bits
        """
        self._read_discrete_inputs_calls.append((address, count, kwargs))

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self._read_operations.append(f"read_discrete_inputs({address}, {count})")

        custom_bits = self._discrete_inputs.get(address)
        if custom_bits is not None:
            # Build a full-length list with custom values at the correct address
            bits = list(self.demo_data.get("discrete_inputs", []))
            for i, val in enumerate(custom_bits):
                if address + i < len(bits):
                    bits[address + i] = val
        else:
            # Pass the full list (FakeModbusResponse handles address lookup)
            bits = self.demo_data.get("discrete_inputs", [])

        return FakeModbusResponse(bits, address, count, is_bits=True)

    async def read_coils(self, address: int, count: int, **kwargs):
        """Simulate reading coils.

        Args:
            address: Coil address (1-based)
            count: Number of coils to read
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            Mock response with bits
        """
        self._read_coils_calls.append((address, count, kwargs))

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self._read_operations.append(f"read_coils({address}, {count})")

        custom_bits = self._coils.get(address)
        if custom_bits is not None:
            # Build a full-length list with custom values at the correct address
            bits = list(self.demo_data.get("coils", []))
            for i, val in enumerate(custom_bits):
                if address + i < len(bits):
                    bits[address + i] = val
        else:
            # Pass the full list (FakeModbusResponse handles address lookup)
            bits = self.demo_data.get("coils", [])

        return FakeModbusResponse(bits, address, count, is_bits=True)

    async def write_register(self, address: int, value: int, **kwargs):
        """Simulate writing a single holding register.

        Args:
            address: Register address (1-based)
            value: Value to write
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            Mock response
        """
        self._write_register_calls.append((address, value, kwargs))

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self._write_operations.append(f"write_register({address}, {value})")
        self._holding_registers[address] = [value]

        return FakeModbusResponse([], address, 0)

    async def write_coil(self, address: int, value: bool, **kwargs):
        """Simulate writing a single coil.

        Args:
            address: Coil address (1-based)
            value: Value to write
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            Mock response
        """
        self._write_coil_calls.append((address, value, kwargs))

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self._write_operations.append(f"write_coil({address}, {value})")
        self._coils[address] = [value]

        return FakeModbusResponse([], address, 0, is_bits=True)

    async def write_holding_register(self, address: int, value: int):
        """Simulate writing a holding register (compatible with ModbusClientInterface).

        Args:
            address: Register address
            value: Value to write

        Returns:
            Mock response
        """
        return await self.write_register(address, value)

    async def write_coil_register(self, address: int, value: bool):
        """Simulate writing a coil (compatible with ModbusClientInterface).

        Args:
            address: Coil address
            value: Value to write

        Returns:
            Mock response
        """
        return await self.write_coil(address, value)

    @property
    def demo_data(self) -> dict:
        """Get demo data, generating it lazily on first access."""
        if not self._demo_data_loaded:
            self._demo_data = self.generate_demo_register_data()
            self._demo_data_loaded = True
        return self._demo_data

    @classmethod
    def generate_demo_register_data(cls) -> dict:
        """Generate demo register data with class-level caching.

        The demo data is generated once and cached at the class level to avoid
        excessive memory usage when many client instances are created (e.g.,
        in connection pool tests).

        Returns:
            Dict with input_registers, holding_registers, discrete_inputs, coils lists.
        """
        # Return cached data if available
        if cls._class_demo_data is not None:
            return cls._class_demo_data

        data = cls._generate_demo_register_data()
        cls._class_demo_data = data
        return data

    @staticmethod
    def _generate_demo_register_data() -> dict:
        """Generate realistic demo register data for testing.

        Returns:
            Dict with input_registers, holding_registers, discrete_inputs, coils lists.
        """
        from tests.fakes.responses import generate_demo_register_data

        return generate_demo_register_data()

    def set_register_value(self, register_type: str, address: int, values: list):
        """Set register values for testing.

        Args:
            register_type: Type of register ('input', 'holding', 'discrete', 'coil')
            address: Register address
            values: List of values to set
        """
        if register_type == "input":
            self._registers.setdefault("input", {})[address] = values
        elif register_type == "holding":
            self._holding_registers[address] = values
        elif register_type == "discrete":
            self._discrete_inputs[address] = values
        elif register_type == "coil":
            self._coils[address] = values

    def get_connection_count(self) -> int:
        """Get the number of connection attempts."""
        return self._connection_count

    def get_operation_count(self) -> int:
        """Get the total number of operations performed."""
        return self._operation_count

    @property
    def connection_count(self) -> int:
        """Get the number of connection attempts (backward compatibility)."""
        return self._connection_count

    @property
    def read_count(self) -> int:
        """Get the number of read operations."""
        return len(self._read_operations)

    @property
    def write_count(self) -> int:
        """Get the number of write operations."""
        return len(self._write_operations)

    @property
    def operation_count(self) -> int:
        """Get the total number of operations performed."""
        return self._operation_count

    def get_read_operations(self) -> list:
        """Get the list of read operations performed."""
        return self._read_operations.copy()

    def get_write_operations(self) -> list:
        """Get the list of write operations performed."""
        return self._write_operations.copy()

    def reset(self):
        """Reset client state for testing."""
        self._connection_count = 0
        self._operation_count = 0
        self._read_operations.clear()
        self._write_operations.clear()
        self._registers.clear()
        self._coils.clear()
        self._discrete_inputs.clear()
        self._holding_registers.clear()
        self._connect_calls.clear()
        self._close_calls.clear()
        self._read_input_registers_calls.clear()
        self._read_holding_registers_calls.clear()
        self._read_discrete_inputs_calls.clear()
        self._read_coils_calls.clear()
        self._write_register_calls.clear()
        self._write_coil_calls.clear()

    # Mock-compatible assertion methods
    def assert_called_once(self):
        """Assert that connect was called exactly once."""
        if len(self._connect_calls) != 1:
            raise AssertionError(
                f"Expected connect to be called once, but was called {len(self._connect_calls)} times"
            )

    def assert_not_called(self):
        """Assert that close was not called."""
        if len(self._close_calls) > 0:
            raise AssertionError(
                f"Expected close to not be called, but was called {len(self._close_calls)} times"
            )
