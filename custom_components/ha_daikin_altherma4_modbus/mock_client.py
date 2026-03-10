"""Mock Modbus client for demo mode."""

import asyncio
import logging
from typing import Any, List

from .client_interface import ModbusClientInterface

_LOGGER = logging.getLogger(__name__)


class MockModbusTcpClient(ModbusClientInterface):
    """Mock Modbus TCP client for demo mode."""

    def __init__(self, host: str, port: int = 502):
        self.host = host
        self.port = port
        self._connected = False
        self._data_regenerated = False  # Flag to track data regeneration
        # Force regeneration of demo data to ensure new enum logic is used
        self._demo_data = self.generate_demo_register_data()
        _LOGGER.info(
            f"Mock Modbus client initialized with {len(self._demo_data['input_registers'])} input registers"
        )

    @property
    def connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def connect(self) -> None:
        """Mock connection - always succeeds."""
        await asyncio.sleep(0.01)  # Simulate connection delay
        self._connected = True
        _LOGGER.debug(f"Mock Modbus client connected to {self.host}:{self.port}")

    async def disconnect(self) -> None:
        """Mock disconnection - always succeeds."""
        self._connected = False
        _LOGGER.debug(f"Mock Modbus client disconnected from {self.host}:{self.port}")

    async def read_input_registers(
        self, address: int, count: int
    ) -> "MockModbusResponse":
        """Mock read input registers."""
        self._demo_data = self.generate_demo_register_data()

        return MockModbusResponse(self._demo_data["input_registers"], address, count)

    async def read_holding_registers(
        self, address: int, count: int
    ) -> "MockModbusResponse":
        """Mock read holding registers."""
        self._demo_data = self.generate_demo_register_data()

        return MockModbusResponse(self._demo_data["holding_registers"], address, count)

    async def read_discrete_inputs(
        self, address: int, count: int
    ) -> "MockModbusResponse":
        """Mock read discrete inputs."""
        self._demo_data = self.generate_demo_register_data()

        return MockModbusResponse(
            self._demo_data["discrete_inputs"], address, count, is_bits=True
        )

    async def read_coils(self, address: int, count: int) -> "MockModbusResponse":
        """Mock read coils."""
        self._demo_data = self.generate_demo_register_data()

        # Convert 1-based address to 0-based for internal use
        return MockModbusResponse(
            self._demo_data["coils"], address, count, is_bits=True
        )

    async def write_holding_register(
        self, address: int, value: int
    ) -> "MockModbusResponse":
        """Mock write holding register."""
        # Convert 1-based address to 0-based for internal use
        internal_address = address - 1
        # Update the mock data
        if 0 <= internal_address < len(self._demo_data["holding_registers"]):
            self._demo_data["holding_registers"][internal_address] = value
        _LOGGER.debug(f"Mock write holding register {address} with value {value}")
        return MockModbusResponse([], 0, 0)  # Success response

    async def write_coil_register(
        self, address: int, value: bool
    ) -> "MockModbusResponse":
        """Mock write coil."""
        # Convert 1-based address to 0-based for internal use
        internal_address = address - 1
        # Update the mock data
        if 0 <= internal_address < len(self._demo_data["coils"]):
            self._demo_data["coils"][internal_address] = value
        _LOGGER.debug(f"Mock write coil {address} with value {value}")
        return MockModbusResponse([], 0, 0)  # Success response

    @staticmethod
    def generate_demo_register_data() -> dict:
        """Generate realistic demo data for all register types based on const.py."""
        import random

        from .const import (
            HOLDING_REGISTERS,
            HOLDING_SWITCHES,
            INPUT_REGISTERS,
            SELECT_REGISTERS,
        )

        # Use fixed seed for deterministic mock data
        # random.seed(42)  # Commented out for true randomness

        # Input registers - only generate registers that are actually defined
        input_registers = []
        max_address = (
            max([reg.get("address", 0) for reg in INPUT_REGISTERS])
            if INPUT_REGISTERS
            else 0
        )

        for i in range(max_address + 1):
            address = i

            # Find corresponding register definition
            register_def = None
            for reg in INPUT_REGISTERS:
                if reg.get("address") == address:
                    register_def = reg
                    break

            if register_def:
                # Specific values by address (not by name)
                if address == 1:  # Leaving water temperature
                    value = 3240  # 32.0°C
                elif address == 2:  # Leaving water temperature BUH
                    value = 3045  # 30.45°C
                elif address == 3:  # Return water temperature
                    value = 2940  # 29.40°C
                elif address == 4:  # DHW temperature
                    value = 4540  # 45.0°C
                elif address == 5:  # Outside air temperature
                    value = 1240  # 12.0°C
                elif address == 6:  # Flow rate
                    value = 1540  # 15.0 L/min
                elif address == 7:  # Remote control room temperature
                    value = 32765  # not available
                elif address == 8:  # Heat pump power consumption
                    value = 500  # 500W
                elif address in [
                    9,
                    10,
                    11,
                ]:  # Compressor, Circulation pump, Booster heater
                    value = random.choice([1])
                elif address == 12:  # Disinfection operation
                    value = 0
                elif address == 13:  # Defrost/Restart
                    value = 0
                elif address == 14:  # Hot start
                    value = 0
                elif address == 15:  # Fernbedienung Raumtemperatur(Zusatz)
                    value = 32765
                elif address == 21:  # Fernbedienung Raumtemperatur(Zusatz)
                    value = 0
                elif address == 37:  # 3-way valve
                    value = random.choice([0, 1])  # Space heating, DHW
                elif address == 38:
                    value = 1
                elif address == 40:
                    value = 3250
                elif address == 41:
                    value = 2750  # 27.5°C
                elif address == 42:
                    value = 2850  # 28.5°C
                elif address == 43:
                    value = 2950  # 29.5°C
                elif address == 51:
                    value = 45
                elif address == 52:  # DHW normal operation
                    value = 1  # Operation
                elif address == 53:
                    value = 1
                elif address == 63:
                    value = 1
                elif address == 65:
                    value = 0
                elif address == 79:  # Wasserdruck
                    value = 90  # 0.9 bar (90 * 0.01)
                elif address == 78:  # Remote controller room temperature (Add)
                    value = 2100  # 21.0°C
                elif address == 80:  # Space heating/cooling target for Main zone Temp16
                    value = 2200  # 22.0°C
                elif address == 81:  # Space heating/cooling target for Add zone
                    value = 2000  # 20.0°C
                elif address == 82:  # Abnormality counter (user)
                    value = 0  # No abnormalities
                elif address == 84:  # Room Heating setpoint Lower limit Temp16
                    value = 1200  # 12.0°C
                elif address == 85:  # Room Heating setpoint Upper limit
                    value = 3000  # 30.0°C
                elif address == 86:  # Room Cooling setpoint Lower limit
                    value = 1200  # 12.0°C
                elif address == 87:  # Room Cooling setpoint Upper limit
                    value = 3500  # 35.0°C
                # Check if it's an enum register
                elif "enum_map" in register_def:
                    enum_keys = [
                        k for k in register_def["enum_map"].keys() if isinstance(k, int)
                    ]
                    if enum_keys:
                        value = random.choice(enum_keys)
                    else:
                        value = 32766  # Default value
                else:
                    # Generate value based on register definition
                    scale = register_def.get("scale", 1)
                    min_val = register_def.get("min_value", 0)
                    max_val = register_def.get("max_value", 100)

                    # Generate scaled value within range
                    scaled_value = random.uniform(min_val, max_val)
                    value = int(scaled_value / scale)
            else:
                value = 32766  # Default for undefined registers

            input_registers.append(value)

        # Holding registers - only generate registers that are actually defined
        holding_registers = []
        max_address = (
            max(
                [
                    reg.get("address", 0)
                    for reg in HOLDING_REGISTERS + HOLDING_SWITCHES + SELECT_REGISTERS
                ]
            )
            if (HOLDING_REGISTERS + HOLDING_SWITCHES + SELECT_REGISTERS)
            else 0
        )

        for i in range(max_address + 1):
            address = i

            # Find corresponding register definition
            register_def = None
            for reg in HOLDING_REGISTERS + HOLDING_SWITCHES + SELECT_REGISTERS:
                if reg.get("address") == address:
                    register_def = reg
                    break

            if register_def:
                # Check if it's an enum register (SELECT_REGISTERS)
                if "enum_map" in register_def:
                    enum_keys = [
                        k for k in register_def["enum_map"].keys() if isinstance(k, int)
                    ]
                    if enum_keys:
                        value = random.choice(enum_keys)
                    else:
                        value = 0  # Default value
                elif register_def.get("name") in [
                    "Operation mode",
                    "Space heating/cooling",
                    "DHW mode setting",
                ]:
                    # Handle specific select registers
                    if register_def.get("name") == "Operation mode":
                        value = random.choice(
                            [0, 1, 2]
                        )  # Stop, Tank Heat Up, Space heating
                    elif register_def.get("name") == "Space heating/cooling":
                        value = random.choice([0, 1])  # Space heating, DHW
                    elif register_def.get("name") == "DHW mode setting":
                        value = random.choice(
                            [0, 1, 2]
                        )  # Reheat, Schedule and reheat, Scheduled
                    else:
                        value = 0
                elif register_def.get("name") in [
                    "Holiday mode",
                    "Smart Grid Operation Mode",
                    "Weather-dependent mode",
                ]:
                    # Handle specific switch registers
                    if register_def.get("name") == "Holiday mode":
                        value = random.choice([0, 1])  # OFF, ON
                    elif register_def.get("name") == "Smart Grid Operation Mode":
                        value = random.choice(
                            [0, 1, 2, 3]
                        )  # Free running, Forced off, Recommended on, Forced on
                    elif register_def.get("name") == "Weather-dependent mode":
                        value = random.choice([0, 1])  # OFF, ON
                    else:
                        value = 0
                else:
                    # Generate value based on register definition
                    scale = register_def.get("scale", 1)
                    min_val = register_def.get("min_value", 0)
                    max_val = register_def.get("max_value", 100)

                    # Generate scaled value within range
                    scaled_value = random.uniform(min_val, max_val)
                    value = int(scaled_value / scale)
            else:
                value = 0  # Default for undefined registers

            holding_registers.append(value)

        # Discrete inputs (addresses 1-26, with index 0 as filler)
        discrete_inputs = []
        for i in range(27):  # 0-26 (0=filler, 1-26=addresses)
            # Generate realistic discrete input values
            if i == 0:  # Index 0: Filler for address alignment
                value = False
            else:
                value = random.choice([False, True])

            discrete_inputs.append(value)

        # Coils (addresses 1-3, with index 0 as filler)
        coils = []
        for i in range(4):  # 0-3 (0=filler, 1-3=addresses)
            # Generate realistic coil values
            if i == 0:  # Index 0: Filler for address alignment
                value = False
            elif i == 1:  # Address 1
                value = True
            elif i == 2:  # Address 2
                value = True
            elif i == 3:  # Address 3
                value = False
            else:
                value = False

            coils.append(value)
        return {
            "input_registers": input_registers,
            "holding_registers": holding_registers,
            "discrete_inputs": discrete_inputs,
            "coils": coils,
        }


class MockModbusResponse:
    """Mock Modbus response with 1-based indexing."""

    def __init__(
        self, data: List[Any], address: int, count: int, is_bits: bool = False
    ):
        self.is_bits = is_bits
        self._error = False

        if is_bits:
            # For discrete inputs and coils - create 1-based array
            # Size should be max(address + count) + 1 for 1-based indexing
            max_index = max(address + count, len(data)) + 1
            self.bits = [False] * max_index  # Index 0 is dummy
            for i in range(count):
                if address + i < len(data):
                    self.bits[address + i] = data[address + i]
                else:
                    self.bits[address + i] = False
        else:
            # For input and holding registers - create 1-based array
            # Size should be max(address + count) + 1 for 1-based indexing
            max_index = max(address + count, len(data)) + 1
            self.registers = [32766] * max_index  # Index 0 is dummy
            for i in range(count):
                if address + i < len(data):
                    self.registers[address + i] = data[address + i]
                else:
                    self.registers[address + i] = (
                        32766  # Default value for out of range
                    )

    def is_error(self) -> bool:
        """Return error status."""
        return self._error
