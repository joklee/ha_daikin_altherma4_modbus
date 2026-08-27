"""Test to verify mock client doesn't generate invalid 16-bit values."""

import sys
import types
from pathlib import Path

import pytest


def _reset_modules(*names: str) -> None:
    for name in names:
        sys.modules.pop(name, None)


def _install_fake_package(monkeypatch) -> str:
    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    monkeypatch.setitem(sys.modules, package_name, package_module)
    return package_name


def _load_mock_client_module(monkeypatch):
    """Load the mock client module with mocked dependencies."""
    package_name = _install_fake_package(monkeypatch)
    module_name = f"{package_name}.modbus.mock_client"
    modbus_client_name = f"{package_name}.modbus.modbus_client"
    exceptions_name = f"{package_name}.core.exceptions"
    register_constants_name = f"{package_name}.core.register_constants"
    register_types_name = f"{package_name}.core.register_types"
    data_types_name = f"{package_name}.core.data_types"
    const_name = f"{package_name}.core.const"
    client_interface_name = f"{package_name}.modbus.client_interface"

    _reset_modules(
        module_name,
        modbus_client_name,
        exceptions_name,
        register_constants_name,
        register_types_name,
        data_types_name,
        const_name,
        client_interface_name,
    )

    # Mock exceptions module
    exceptions_module = types.ModuleType(exceptions_name)

    class ModbusDeviceException(Exception):
        pass

    exceptions_module.ModbusDeviceException = ModbusDeviceException
    sys.modules[exceptions_name] = exceptions_module

    # Mock modbus_client module
    modbus_client_module = types.ModuleType(modbus_client_name)

    class MockModbusTcpClient:
        def __init__(self, host, port=502):
            self.host = host
            self.port = port
            self.connected = False

        async def connect(self):
            self.connected = True
            return True

        async def disconnect(self):
            self.connected = False

        async def read_input_registers(self, address, count):
            return None

        async def read_holding_registers(self, address, count):
            return None

        async def read_discrete_inputs(self, address, count):
            return None

        async def read_coils(self, address, count):
            return None

        async def write_single_register(self, address, value):
            return None

        async def write_single_coil(self, address, value):
            return None

    modbus_client_module.MockModbusTcpClient = MockModbusTcpClient
    sys.modules[modbus_client_name] = modbus_client_module

    import importlib

    # Install fake parent packages so real __init__.py files are not executed
    base_path = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    for sub in ("modbus", "core"):
        parent_name = f"{package_name}.{sub}"
        parent = types.ModuleType(parent_name)
        parent.__path__ = [str(base_path / sub)]
        sys.modules[parent_name] = parent

    # Import the module
    module = importlib.import_module(module_name)

    # Clean up
    _reset_modules(
        module_name,
        modbus_client_name,
        exceptions_name,
        register_constants_name,
        register_types_name,
        data_types_name,
        const_name,
        client_interface_name,
    )

    return module


@pytest.mark.parametrize(
    "test_case",
    [
        {
            "name": "temperature_values",
            "address": 40,
            "count": 6,
            "register_type": "input",
            "validation_func": lambda value: -3000 <= value <= 10000,
            "description": "Temperature values should be in reasonable range (-30°C to 100°C = -3000 to 10000 raw)",
            "needs_signed_conversion": True,
        },
        {
            "name": "power_values",
            "address": 51,
            "count": 1,
            "register_type": "input",
            "validation_func": lambda value: 0 <= value <= 2000,
            "description": "Power in kW * 100, reasonable range 0-20kW = 0-2000",
            "needs_signed_conversion": False,
        },
        {
            "name": "flow_values",
            "address": 49,
            "count": 1,
            "register_type": "input",
            "validation_func": lambda value: 0 <= value <= 10000,
            "description": "Flow in L/min * 100, reasonable range 0-100 L/min = 0-10000",
            "needs_signed_conversion": False,
        },
    ],
)
@pytest.mark.asyncio
async def test_mock_client_register_values(monkeypatch, test_case):
    """Test that mock client generates realistic register values."""
    mock_client_module = _load_mock_client_module(monkeypatch)
    MockModbusTcpClient = mock_client_module.MockModbusTcpClient

    client = MockModbusTcpClient("192.168.1.100", 502)
    await client.connect()

    # Select the appropriate read method based on register type
    if test_case["register_type"] == "input":
        response = await client.read_input_registers(
            test_case["address"], test_case["count"]
        )
    elif test_case["register_type"] == "holding":
        response = await client.read_holding_registers(
            test_case["address"], test_case["count"]
        )
    else:
        raise ValueError(f"Unsupported register type: {test_case['register_type']}")

    assert response is not None

    # Validate each register value
    for i in range(test_case["count"]):
        addr = test_case["address"] + i
        if addr < len(response.registers):
            value = response.registers[addr]

            # Apply signed conversion if needed
            if test_case["needs_signed_conversion"] and value > 32767:
                value = value - 65536

            assert test_case["validation_func"](value), (
                f"{test_case['description']}. "
                f"Register {addr} value {value} out of realistic range"
            )

    await client.disconnect()


@pytest.mark.parametrize(
    "register_test_case",
    [
        {
            "name": "holding_registers",
            "address": 0,
            "count": 10,
            "read_method": "read_holding_registers",
            "validation": "unsigned_16bit",
            "description": "Holding registers should be valid unsigned 16-bit values",
        },
        {
            "name": "input_registers",
            "address": 40,
            "count": 10,
            "read_method": "read_input_registers",
            "validation": "signed_16bit",
            "description": "Input registers should be valid signed 16-bit values",
        },
    ],
)
@pytest.mark.parametrize(
    "bit_test_case",
    [
        {
            "name": "discrete_inputs",
            "read_method": "read_discrete_inputs",
            "description": "Discrete inputs should return boolean values",
        },
        {
            "name": "coils",
            "read_method": "read_coils",
            "description": "Coils should return boolean values",
        },
    ],
)
@pytest.mark.asyncio
async def test_mock_client_all_registers(
    monkeypatch, register_test_case, bit_test_case
):
    """Test that mock client can read all register types.

    This test is parametrized to run:
    - 2 register type cases (holding, input)
    - 2 bit type cases (discrete inputs, coils)

    Total: 4 test cases.
    """
    mock_client_module = _load_mock_client_module(monkeypatch)
    MockModbusTcpClient = mock_client_module.MockModbusTcpClient

    client = MockModbusTcpClient("192.168.1.100", 502)
    await client.connect()

    # Test register types (holding/input registers)
    address = register_test_case["address"]
    count = register_test_case["count"]

    if register_test_case["read_method"] == "read_holding_registers":
        response = await client.read_holding_registers(address, count)
    else:
        response = await client.read_input_registers(address, count)

    assert response is not None
    assert hasattr(response, "registers")
    # Check that we got at least the requested number of registers
    assert len(response.registers) >= address + count

    # Validate register values based on type
    if register_test_case["validation"] == "unsigned_16bit":
        for i in range(count):
            value = response.registers[address + i]
            assert 0 <= value <= 65535, (
                f"{register_test_case['description']}. "
                f"Register {address + i} value {value} not in 0-65535 range"
            )
    else:  # signed_16bit
        for i in range(count):
            value = response.registers[address + i]
            # Convert unsigned to signed if needed
            if value > 32767:
                value = value - 65536
            assert -32768 <= value <= 32767, (
                f"{register_test_case['description']}. "
                f"Register {address + i} value {value} not in -32768-32767 range"
            )

    # Test bit types (discrete inputs/coils)
    # Both use the same address pattern (start at 1, read 10)
    bit_read_method = bit_test_case["read_method"]

    if bit_read_method == "read_discrete_inputs":
        response = await client.read_discrete_inputs(1, 10)
    else:
        response = await client.read_coils(1, 10)

    assert response is not None
    assert hasattr(response, "bits")
    # Check that we got at least the requested number of bits (skip index 0)
    assert len(response.bits) >= 11  # Need at least 11 to have indices 1-10

    for addr in range(1, 11):  # Check indices 1-10
        if addr < len(response.bits):
            value = response.bits[addr]
            assert isinstance(value, bool), (
                f"{bit_test_case['description']}. "
                f"{bit_test_case['name'].replace('_', ' ').title()} "
                f"{addr} value {value} is not a boolean"
            )

    await client.disconnect()
