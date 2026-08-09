#!/usr/bin/env python3
"""
Shared test utilities for Daikin Altherma 4 Modbus integration tests.
"""

import asyncio
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock


class MockConst:
    """Mock Home Assistant constants."""

    EntityCategory = Mock()
    EntityCategory.DIAGNOSTIC = "diagnostic"
    UnitOfTemperature = "°C"


class MockDataUpdateCoordinator:
    """Mock DataUpdateCoordinator for testing."""

    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = {}

    async def async_config_entry_first_refresh(self):
        """Mock initial refresh used during integration setup."""
        return


class UpdateFailed(Exception):
    """Mock UpdateFailed exception."""


class MockSensorEntity:
    """Mock SensorEntity for testing."""

    def __init__(self):
        self._attr_device_class = None
        self._attr_state_class = None
        self._attr_unique_id = None
        self._attr_native_unit_of_measurement = None
        self._attr_last_reset = None
        self._attr_last_reported = None


def setup_home_assistant_mocks():
    """Set up all Home Assistant module mocks."""
    # Only set up mocks if conftest.py hasn't already set up proper stubs
    # conftest.py sets up proper stubs with correct metaclass hierarchy
    # which is needed for multiple inheritance (e.g. CoordinatorEntity + BinarySensorEntity)
    if "homeassistant" in sys.modules and isinstance(
        sys.modules["homeassistant"], types.ModuleType
    ):
        # conftest.py already set up proper stubs - don't overwrite them
        return

    # Install mocks
    sys.modules["homeassistant"] = Mock()
    sys.modules["homeassistant.exceptions"] = Mock()
    sys.modules["homeassistant.exceptions"].ConfigEntryNotReady = Exception
    sys.modules["homeassistant.const"] = MockConst()
    sys.modules["homeassistant.core"] = Mock()
    sys.modules["homeassistant.helpers"] = Mock()
    sys.modules["homeassistant.helpers.typing"] = Mock()
    sys.modules["homeassistant.helpers.typing"].ConfigType = Mock()
    sys.modules["homeassistant.helpers.update_coordinator"] = Mock()
    sys.modules[
        "homeassistant.helpers.update_coordinator"
    ].data_update_coordinator = MockDataUpdateCoordinator
    sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = UpdateFailed
    sys.modules["homeassistant.components"] = Mock()
    sys.modules["homeassistant.components.sensor"] = Mock()
    sys.modules["homeassistant.components.sensor"].SensorEntity = MockSensorEntity


def setup_project_paths():
    """Set up project paths for testing."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    return project_root


def load_const_module(project_root):
    """Load the const module for testing."""
    # Add the custom_components path to sys.path to allow imports
    import os
    import sys

    custom_components_parent = str(project_root / "custom_components")
    if custom_components_parent not in sys.path:
        sys.path.insert(0, custom_components_parent)

    # Change to the custom_components directory to make relative imports work
    original_cwd = os.getcwd()
    try:
        os.chdir(custom_components_parent)

        # Import the module properly
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ha_daikin_altherma4_modbus.const", "ha_daikin_altherma4_modbus/const.py"
        )
        const_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(const_module)

        return const_module
    finally:
        os.chdir(original_cwd)


def load_register_constants_module(project_root):
    """Load the register_constants module for testing."""
    # Add the custom_components path to sys.path to allow imports
    import os
    import sys

    custom_components_parent = str(project_root / "custom_components")
    if custom_components_parent not in sys.path:
        sys.path.insert(0, custom_components_parent)

    # Change to the custom_components directory to make relative imports work
    original_cwd = os.getcwd()
    try:
        os.chdir(custom_components_parent)

        # Import the modules properly
        import importlib.util

        # First load register_types so register_constants' relative import works
        register_types_spec = importlib.util.spec_from_file_location(
            "ha_daikin_altherma4_modbus.register_types",
            "ha_daikin_altherma4_modbus/register_types.py",
        )
        register_types_module = importlib.util.module_from_spec(register_types_spec)
        sys.modules["ha_daikin_altherma4_modbus.register_types"] = register_types_module
        register_types_spec.loader.exec_module(register_types_module)

        # Now load register_constants which imports from .register_types
        spec = importlib.util.spec_from_file_location(
            "ha_daikin_altherma4_modbus.register_constants",
            "ha_daikin_altherma4_modbus/register_constants.py",
        )
        register_constants_module = importlib.util.module_from_spec(spec)
        sys.modules["ha_daikin_altherma4_modbus.register_constants"] = (
            register_constants_module
        )
        spec.loader.exec_module(register_constants_module)

        return register_constants_module
    finally:
        os.chdir(original_cwd)


def create_mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = Mock()
    coordinator.data = {}
    return coordinator


def create_test_trigger_time():
    """Create a consistent test trigger time."""
    return datetime(2024, 3, 2, 20, 30, 0, tzinfo=timezone.utc)


def setup_sensor_test_module(monkeypatch):
    """Set up sensor module testing environment for centralized mocking.

    This function centralizes the mocking approach for testing the sensor module
    by creating all necessary fake modules and stubs. It avoids duplicating
    module stubbing code across test files.

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        The loaded sensor module
    """
    import importlib

    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )

    # Reset modules to ensure clean state
    for name in list(sys.modules):
        if name.startswith(package_name):
            monkeypatch.delitem(sys.modules, name, raising=False)

    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    package_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, package_name, package_module)

    sensor_module_name = f"{package_name}.sensor"
    common_module_name = f"{package_name}.common"
    config_utils_name = f"{package_name}.config_entry_utils"
    register_constants_name = f"{package_name}.register_constants"
    register_types_name = f"{package_name}.register_types"
    repair_name = f"{package_name}.repair"
    const_name = f"{package_name}.const"

    # Create register_types module with all register classes
    register_types_module = types.ModuleType(register_types_name)

    class SensorRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class CalculatedRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class NumberRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class SelectRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class SwitchRegister:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class BIT:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    register_types_module.SensorRegister = SensorRegister
    register_types_module.CalculatedRegister = CalculatedRegister
    register_types_module.NumberRegister = NumberRegister
    register_types_module.SelectRegister = SelectRegister
    register_types_module.SwitchRegister = SwitchRegister
    register_types_module.BIT = BIT

    # Add register type constants with proper attributes
    class MockRegisterDataType:
        def __init__(self, name, signed, bits, scaling, range=None):
            self.name = name
            self.signed = signed
            self.bits = bits
            self.scaling = scaling
            self.range = range

    register_types_module.RegisterDataType = MockRegisterDataType
    register_types_module.TEMP16 = MockRegisterDataType(
        "Temp16", True, 16, 0.01, (-327.68, 327.67)
    )
    register_types_module.INT16 = MockRegisterDataType(
        "Int16", True, 16, 1, (-32768, 32767)
    )
    register_types_module.INT16S100 = MockRegisterDataType(
        "Int16", True, 16, 0.01, (-32768, 32767)
    )
    register_types_module.TEXT16 = MockRegisterDataType("Text16", False, 16, 1, None)
    register_types_module.POW16 = MockRegisterDataType(
        "Pow16", True, 16, 0.01, (-327.68, 327.67)
    )
    register_types_module.BIT = MockRegisterDataType("Bit", False, 1, 1, (0, 1))
    register_types_module.TIMESTAMP16 = MockRegisterDataType(
        "Timestamp16", True, 16, 1, (-32768, 32767)
    )

    monkeypatch.setitem(sys.modules, register_types_name, register_types_module)

    # Create const module
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.INPUT_DEVICE_INFO = {}
    const_module.CALCULATED_DEVICE_INFO = {}
    const_module.REGISTER_FLOW_RATE = "input_49"
    const_module.REGISTER_LEAVING_WATER_TEMP = "input_40"
    const_module.REGISTER_RETURN_WATER_TEMP = "input_42"
    const_module.REGISTER_HEAT_PUMP_POWER = "input_51"
    const_module.SPECIAL_REGISTER_NOT_SUPPORTED = 32767
    const_module.SPECIAL_REGISTER_NOT_AVAILABLE = 32766
    const_module.SPECIAL_REGISTER_WAITING = 32765
    const_module.SPECIAL_REGISTER_VALUES = frozenset({32765, 32766, 32767})
    const_module.INPUT_REGISTERS = [
        SensorRegister(
            name="Flow rate",
            address=49,
            input_type="input",
            register_name="input_49",
            unit="L/min",
            data_type=register_types_module.POW16,
        ),
        SensorRegister(
            name="Leaving water temperature PHE",
            address=40,
            input_type="input",
            register_name="input_40",
            unit="°C",
            data_type=register_types_module.TEMP16,
        ),
        SensorRegister(
            name="Return water temperature",
            address=42,
            input_type="input",
            register_name="input_42",
            unit="°C",
            data_type=register_types_module.TEMP16,
        ),
        SensorRegister(
            name="Heat pump power consumption",
            address=51,
            input_type="input",
            register_name="input_51",
            unit="W",
            data_type=register_types_module.POW16,
        ),
    ]
    const_module.CALCULATED_SENSORS = [
        CalculatedRegister(
            name="Coefficient of Performance",
            address=0,
            input_type="calculated",
            register_name="cop",
            calc_type="cop",
            unit="CoP",
            translation_key="cop",
        ),
    ]
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Create register_constants module (re-exports from const)
    register_constants_module = types.ModuleType(register_constants_name)
    register_constants_module.INPUT_REGISTERS = const_module.INPUT_REGISTERS
    register_constants_module.CALCULATED_SENSORS = const_module.CALCULATED_SENSORS
    register_constants_module.INPUT_DEVICE_INFO = const_module.INPUT_DEVICE_INFO
    register_constants_module.CALCULATED_DEVICE_INFO = (
        const_module.CALCULATED_DEVICE_INFO
    )
    monkeypatch.setitem(sys.modules, register_constants_name, register_constants_module)

    # Create common module
    common_module = types.ModuleType(common_module_name)

    def get_register_value(data):
        if isinstance(data, dict):
            return data.get("value")
        return None

    def get_register_scale(data):
        if isinstance(data, dict):
            return data.get("scale")
        return None

    def is_entity_available(data, register_name):
        return True

    def is_unavailable_value(val):
        return val in [32765, 32766]

    def to_signed_16bit(val):
        if val > 32767:
            return val - 65536
        return val

    def get_coordinator_from_entry(hass, entry):
        return getattr(entry, "runtime_data", None) or getattr(
            entry, "coordinator", None
        )

    common_module.get_register_value = get_register_value
    common_module.get_register_scale = get_register_scale
    common_module.is_entity_available = is_entity_available
    common_module.is_unavailable_value = is_unavailable_value
    common_module.to_signed_16bit = to_signed_16bit
    common_module.get_coordinator_from_entry = get_coordinator_from_entry
    monkeypatch.setitem(sys.modules, common_module_name, common_module)

    # Create config_entry_utils module
    config_utils_module = types.ModuleType(config_utils_name)

    def entry_value(entry, key, default=None):
        options = getattr(entry, "options", {}) or {}
        data = getattr(entry, "data", {}) or {}
        return options.get(key, data.get(key, default))

    config_utils_module.entry_value = entry_value
    monkeypatch.setitem(sys.modules, config_utils_name, config_utils_module)

    # Create repair module
    repair_module = types.ModuleType(repair_name)
    repair_module.async_create_abnormality_issue = lambda *a, **kw: None
    repair_module.async_delete_abnormality_issue = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, repair_name, repair_module)

    return importlib.import_module(sensor_module_name)


class FakeModbusClient:
    """Centralized fake Modbus client for testing.

    This class provides a realistic mock of AsyncModbusTcpClient behavior
    for testing purposes, eliminating the need for scattered MagicMock
    configurations across test files.
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

        # Backward compatibility: expose as properties
        self.connection_count = 0
        self.operation_count = 0

        # Demo data for coverage tests compatibility (lazy-loaded)
        self._demo_data = None
        self._demo_data_loaded = False

    async def connect(self):
        """Simulate connection with realistic timing."""
        await asyncio.sleep(0.001)  # 1ms connection time
        self.connected = True
        self._connection_count += 1
        self.connection_count = self._connection_count
        self._connect_calls.append(())

    def close(self):
        """Simulate connection close."""
        self.connected = False
        self._close_calls.append(())

    async def disconnect(self):
        """Simulate disconnection (compatible with MockModbusTcpClient)."""
        await asyncio.sleep(0.001)  # 1ms disconnect time
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
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_input_registers({address}, {count})")

        # Use custom register values if set, otherwise fall back to demo data
        custom_registers = self._registers.get("input", {}).get(address)
        if custom_registers is not None:
            registers = custom_registers
        else:
            demo_input = self.demo_data.get("input_registers", [])
            if address < len(demo_input):
                registers = demo_input[address : address + count]
            else:
                registers = [32766] * count
        if len(registers) < count:
            registers = registers + [32766] * (count - len(registers))

        return FakeModbusResponse(registers[:count], address, count)

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
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_holding_registers({address}, {count})")

        custom_registers = self._holding_registers.get(address)
        if custom_registers is not None:
            registers = custom_registers
        else:
            demo_holding = self.demo_data.get("holding_registers", [])
            if address < len(demo_holding):
                registers = demo_holding[address : address + count]
            else:
                registers = [0] * count
        if len(registers) < count:
            registers = registers + [0] * (count - len(registers))

        return FakeModbusResponse(registers[:count], address, count)

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
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_discrete_inputs({address}, {count})")

        custom_bits = self._discrete_inputs.get(address)
        if custom_bits is not None:
            bits = custom_bits
        else:
            demo_discrete = self.demo_data.get("discrete_inputs", [])
            if address < len(demo_discrete):
                bits = demo_discrete[address : address + count]
            else:
                bits = [False] * count
        if len(bits) < count:
            bits = bits + [False] * (count - len(bits))

        return FakeModbusResponse(bits[:count], address, count, is_bits=True)

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
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_coils({address}, {count})")

        custom_bits = self._coils.get(address)
        if custom_bits is not None:
            bits = custom_bits
        else:
            demo_coils = self.demo_data.get("coils", [])
            if address < len(demo_coils):
                bits = demo_coils[address : address + count]
            else:
                bits = [False] * count
        if len(bits) < count:
            bits = bits + [False] * (count - len(bits))

        return FakeModbusResponse(bits[:count], address, count, is_bits=True)

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
        self.operation_count = self._operation_count
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
        self.operation_count = self._operation_count
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
        # Input registers (addresses 0-87)
        input_registers = [32766] * 88  # Default: unavailable
        input_registers[1] = 3240  # Leaving water temp: 32.4°C
        input_registers[2] = 3045  # Leaving water temp BUH: 30.45°C
        input_registers[3] = 2940  # Return water temp: 29.4°C
        input_registers[4] = 4540  # DHW temp: 45.0°C
        input_registers[5] = 1240  # Outside air temp: 12.0°C
        input_registers[6] = 1540  # Flow rate: 15.0 L/min
        input_registers[8] = 500  # Heat pump power: 500W
        input_registers[9] = 1  # Circulation pump running
        input_registers[10] = 1  # Compressor running
        input_registers[11] = 0  # Booster heater
        input_registers[31] = 1  # Compressor run
        input_registers[32] = 0  # Booster heater run
        input_registers[37] = 0  # 3-way valve: space heating
        input_registers[38] = 1  # Operation mode: heating
        input_registers[40] = 3250  # Leaving water PHE: 32.5°C
        input_registers[41] = 2750  # Leaving water BUH: 27.5°C
        input_registers[42] = 2850  # Return water: 28.5°C
        input_registers[43] = 2950  # DHW: 29.5°C
        input_registers[44] = 65036  # Outside air: -5.0°C (2's complement)
        input_registers[49] = 1540  # Flow rate: 15.0 L/min
        input_registers[51] = 45  # Heat pump power: 0.45 kW
        input_registers[52] = 1  # DHW normal operation
        input_registers[53] = 1  # Space heating/cooling operation
        input_registers[63] = 0  # Disinfection state: unsuccessful
        input_registers[65] = 0  # Demand response: free
        input_registers[79] = 90  # Water pressure: 0.9 bar
        input_registers[80] = 2200  # Target Main zone: 22.0°C
        input_registers[81] = 2000  # Target Add zone: 20.0°C
        input_registers[82] = 0  # Abnormality counter
        input_registers[84] = 1200  # Room Heating lower: 12.0°C
        input_registers[85] = 3000  # Room Heating upper: 30.0°C
        input_registers[86] = 1200  # Room Cooling lower: 12.0°C
        input_registers[87] = 3500  # Room Cooling upper: 35.0°C

        # Holding registers (addresses 0-80)
        holding_registers = [0] * 81
        holding_registers[1] = 2500  # Main Heating setpoint: 25.0°C
        holding_registers[2] = 1800  # Main Cooling setpoint: 18.0°C
        holding_registers[3] = 1  # Operation mode: heating
        holding_registers[4] = 1  # Space heating/cooling ON: on
        holding_registers[6] = 2100  # Room Thermostat Heating Main: 21.0°C
        holding_registers[7] = 2400  # Room Thermostat Cooling Main: 24.0°C
        holding_registers[9] = 0  # Quiet mode: off
        holding_registers[10] = 4800  # DHW reheat setpoint: 48.0°C
        holding_registers[54] = 0  # Main LWT Heating offset
        holding_registers[55] = 0  # Main LWT Cooling offset
        holding_registers[56] = 0  # Smart Grid: free running
        holding_registers[58] = 500  # Imposed power limit: 5.0 kW
        holding_registers[63] = 3500  # Add Heating setpoint: 35.0°C
        holding_registers[64] = 1800  # Add Cooling setpoint: 18.0°C
        holding_registers[66] = 0  # Add LWT Heating offset
        holding_registers[67] = 0  # Add LWT Cooling offset
        holding_registers[68] = 0  # Weather-dependent Heating: fixed
        holding_registers[69] = 0  # Weather-dependent Cooling: fixed
        holding_registers[74] = 0  # Thermostat Request Main: none
        holding_registers[75] = 0  # Thermostat Request Add: none
        holding_registers[76] = 2100  # Room Thermostat Heating Main
        holding_registers[77] = 2400  # Room Thermostat Cooling Main
        holding_registers[78] = 2000  # Room Thermostat Heating Add
        holding_registers[79] = 2300  # Room Thermostat Cooling Add
        holding_registers[80] = 0  # DHW mode: reheat

        # Discrete inputs (addresses 0-26)
        discrete_inputs = [False] * 27
        discrete_inputs[1] = False  # Shut-off valve
        discrete_inputs[11] = True  # Compressor running
        discrete_inputs[19] = True  # DHW running
        discrete_inputs[20] = True  # Main zone running
        discrete_inputs[25] = True  # Circulation pump running

        # Coils (addresses 0-3)
        coils = [False] * 4
        coils[1] = True  # DHW ON
        coils[2] = True  # Main zone ON
        coils[3] = False  # Additional zone OFF

        return {
            "input_registers": input_registers,
            "holding_registers": holding_registers,
            "discrete_inputs": discrete_inputs,
            "coils": coils,
        }

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
        self.connection_count = 0
        self.operation_count = 0
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


class FakeModbusClientPerformance(FakeModbusClient):
    """Performance-optimized variant of FakeModbusClient for benchmarking.

    This subclass adds realistic timing and performance tracking capabilities
    for performance testing scenarios.
    """

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 502,
        timeout: int = 10,
        connected: bool = True,
        timing_mode: str = "realistic",
    ):
        """Initialize performance-optimized fake Modbus client.

        Args:
            host: Mock host address
            port: Mock port
            timeout: Mock timeout
            connected: Initial connection state
            timing_mode: Timing mode ('realistic', 'fast', 'custom')
        """
        super().__init__(host, port, timeout, connected)
        self.timing_mode = timing_mode
        self.total_bytes = 0
        self.read_count = 0

    async def connect(self):
        """Simulate connection with performance timing."""
        if self.timing_mode == "realistic":
            await asyncio.sleep(0.01)  # 10ms connection time
        elif self.timing_mode == "fast":
            await asyncio.sleep(0.001)  # 1ms connection time
        self.connected = True
        self._connection_count += 1
        self._connect_calls.append(())

    async def read_input_registers(self, address: int, count: int, **kwargs):
        """Simulate reading input registers with performance timing."""
        self._read_input_registers_calls.append((address, count, kwargs))
        self.read_count += 1

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_input_registers({address}, {count})")

        # Performance timing
        if self.timing_mode == "realistic":
            await asyncio.sleep(
                0.001 + (count * 0.00001)
            )  # 1ms base + per-register time
        elif self.timing_mode == "fast":
            await asyncio.sleep(0.001)  # Fixed fast timing

        # Track bytes
        self.total_bytes += count * 2  # 2 bytes per register

        registers = self._registers.get("input", {}).get(address, [0] * count)
        if len(registers) < count:
            registers = registers + [0] * (count - len(registers))

        return registers[:count]

    async def read_holding_registers(self, address: int, count: int, **kwargs):
        """Simulate reading holding registers with performance timing."""
        self._read_holding_registers_calls.append((address, count, kwargs))
        self.read_count += 1

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_holding_registers({address}, {count})")

        # Performance timing
        if self.timing_mode == "realistic":
            await asyncio.sleep(0.001 + (count * 0.00001))
        elif self.timing_mode == "fast":
            await asyncio.sleep(0.001)

        # Track bytes
        self.total_bytes += count * 2

        registers = self._holding_registers.get(address, [0] * count)
        if len(registers) < count:
            registers = registers + [0] * (count - len(registers))

        return registers[:count]

    async def read_discrete_inputs(self, address: int, count: int, **kwargs):
        """Simulate reading discrete inputs with performance timing."""
        self._read_discrete_inputs_calls.append((address, count, kwargs))
        self.read_count += 1

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_discrete_inputs({address}, {count})")

        # Performance timing
        if self.timing_mode == "realistic":
            await asyncio.sleep(0.0005)
        elif self.timing_mode == "fast":
            await asyncio.sleep(0.0001)

        # Track bytes (1 bit per discrete input)
        self.total_bytes += count // 8

        bits = self._discrete_inputs.get(address, [False] * count)
        if len(bits) < count:
            bits = bits + [False] * (count - len(bits))

        return bits[:count]

    async def read_coils(self, address: int, count: int, **kwargs):
        """Simulate reading coils with performance timing."""
        self._read_coils_calls.append((address, count, kwargs))
        self.read_count += 1

        if not self.connected:
            raise ConnectionError("Not connected")

        self._operation_count += 1
        self.operation_count = self._operation_count
        self._read_operations.append(f"read_coils({address}, {count})")

        # Performance timing
        if self.timing_mode == "realistic":
            await asyncio.sleep(0.0005)
        elif self.timing_mode == "fast":
            await asyncio.sleep(0.0001)

        # Track bytes
        self.total_bytes += count // 8

        bits = self._coils.get(address, [False] * count)
        if len(bits) < count:
            bits = bits + [False] * (count - len(bits))

        return bits[:count]

    def reset(self):
        """Reset client state for testing."""
        super().reset()
        self.total_bytes = 0
        self.read_count = 0
        self.connection_count = 0
        self.operation_count = 0


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
