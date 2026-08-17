"""Helper functions for loading project modules in tests."""

import importlib.util
import os
import sys
import types
from pathlib import Path
from unittest.mock import Mock


def setup_project_paths():
    """Set up project paths for testing."""
    project_root = Path(__file__).resolve().parents[1].parent
    sys.path.insert(0, str(project_root))
    return project_root


def load_const_module(project_root):
    """Load the const module for testing."""
    # Add the custom_components path to sys.path to allow imports
    custom_components_parent = str(project_root / "custom_components")
    if custom_components_parent not in sys.path:
        sys.path.insert(0, custom_components_parent)

    # Change to the custom_components directory to make relative imports work
    original_cwd = os.getcwd()
    try:
        os.chdir(custom_components_parent)

        # Import the module properly
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
    custom_components_parent = str(project_root / "custom_components")
    if custom_components_parent not in sys.path:
        sys.path.insert(0, custom_components_parent)

    # Change to the custom_components directory to make relative imports work
    original_cwd = os.getcwd()
    try:
        os.chdir(custom_components_parent)

        # Import the modules properly
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
        Path(__file__).resolve().parents[2]
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


def create_mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = Mock()
    coordinator.data = {}
    return coordinator
