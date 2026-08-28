"""Test service actions for ha_daikin_altherma4_modbus integration."""

# Setup mocks before any imports
import sys
import types

# Names that this test module stubs out in ``sys.modules``. Every stub must
# be removed again after use: pytest imports all collected test modules up
# front (even for filtered runs such as ``pytest -m modbus``), so a stub left
# behind would silently replace the real modules for every test module
# collected later in the same session.
_STUB_MODULE_NAMES = (
    "custom_components.ha_daikin_altherma4_modbus.const",
    "custom_components.ha_daikin_altherma4_modbus.core.const",
    "custom_components.ha_daikin_altherma4_modbus.register_constants",
    "custom_components.ha_daikin_altherma4_modbus.core.register_constants",
)

_MISSING = object()

# State of ``sys.modules`` before this module installs any stub.
_saved_sys_modules = {
    name: sys.modules.get(name, _MISSING) for name in _STUB_MODULE_NAMES
}


def _restore_stubbed_modules(saved):
    """Restore the ``sys.modules`` entries captured in *saved*."""
    for name, previous in saved.items():
        if previous is _MISSING:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous


# Mock const module for missing constants
_const_stub_installed = False
if "custom_components.ha_daikin_altherma4_modbus.const" not in sys.modules:
    const_module = types.ModuleType(
        "custom_components.ha_daikin_altherma4_modbus.const"
    )
    const_module.ATTR_CONFIG_ENTRY_ID = "config_entry_id"
    const_module.ATTR_OPERATION_MODE = "operation_mode"
    const_module.ATTR_COIL_ACTIONS = "coil_actions"
    const_module.ATTR_STATE = "state"
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.DEFAULT_PORT = 502
    const_module.SLOW_SCAN_INTERVAL = 30
    const_module.NORMAL_SCAN_INTERVAL = 5
    const_module.MIN_MODBUS_ADDRESS = 1
    const_module.MAX_MODBUS_ADDRESS = 87
    const_module.REGISTER_OPERATION_MODE = "holding_3"
    const_module.REGISTER_DHW_HVAC_MODE = "coil_1"
    const_module.SPECIAL_REGISTER_NOT_SUPPORTED = 32767
    const_module.SPECIAL_REGISTER_NOT_AVAILABLE = 32766
    const_module.SPECIAL_REGISTER_WAITING = 32765
    const_module.SPECIAL_REGISTER_VALUES = frozenset({32767, 32766, 32765})
    # HVAC mode constants
    const_module.HVAC_OFF = 0
    const_module.HVAC_HEAT = 1
    const_module.HVAC_COOL = 2
    # Service name constants
    const_module.SERVICE_SET_OPERATION_MODE = "set_operation_mode"
    const_module.SERVICE_SET_DHW_STATE = "set_dhw_state"
    const_module.SERVICE_SET_MAIN_ZONE_STATE = "set_main_zone_state"
    const_module.SERVICE_SET_ADDITIONAL_ZONE_STATE = "set_additional_zone_state"
    const_module.SERVICE_SET_SMART_GRID_MODE = "set_smart_grid_mode"
    const_module.SERVICE_SET_QUIET_MODE = "set_quiet_mode"
    const_module.SERVICE_SET_DHW_BOOSTER_MODE = "set_dhw_booster_mode"
    const_module.SERVICE_SET_DHW_SINGLE_HEATUP = "set_dhw_single_heatup"
    const_module.SERVICE_SET_POWER_LIMIT = "set_power_limit"
    const_module.SERVICE_SET_HEATING_OFFSET = "set_heating_offset"
    const_module.SERVICE_SET_COOLING_OFFSET = "set_cooling_offset"
    const_module.SERVICE_SET_ROOM_HEATING_SETPOINT = "set_room_heating_setpoint"
    const_module.SERVICE_SET_ROOM_COOLING_SETPOINT = "set_room_cooling_setpoint"
    const_module.SERVICE_SET_ADDITIONAL_ZONE_SETPOINT = "set_additional_zone_setpoint"
    const_module.SERVICE_REFRESH_CONNECTION = "refresh_connection"
    # Config constants required by core/__init__.py
    const_module.CONF_DEMO_MODE = "demo_mode"
    const_module.CONF_ELECTRIC_POWER_SENSOR = "electric_power_sensor"
    const_module.CONF_HA = "ha"
    const_module.CONF_HOST = "host"
    const_module.CONF_INTEGRATION = "integration"
    const_module.CONF_MODBUS = "modbus"
    const_module.CONF_PORT = "port"
    const_module.CONF_SCAN_INTERVAL = "scan_interval"
    const_module.CONF_SLOW = "slow"
    const_module.CONF_SLOW_SCAN_INTERVAL = "slow_scan_interval"
    const_module.CONF_UNIT = "unit"
    sys.modules["custom_components.ha_daikin_altherma4_modbus.const"] = const_module
    sys.modules["custom_components.ha_daikin_altherma4_modbus.core.const"] = (
        const_module
    )
    _const_stub_installed = True

# Mock voluptuous for schema validation tests
try:
    import voluptuous as vol

    print("Using real voluptuous library")
except ImportError:
    # Create minimal mock for voluptuous
    print("Using mock voluptuous")

    class MockVol:
        class Invalid(Exception):
            pass

        class Required:
            def __init__(self, key):
                self.key = key

        class Optional:
            def __init__(self, key):
                self.key = key

        @staticmethod
        def Schema(schema_dict):
            class SchemaValidator:
                def __call__(self, data):
                    print(f"MockSchema validating data: {data}")
                    print(f"Schema dict: {schema_dict}")
                    # Validate each field in the schema
                    for field_spec, validator in schema_dict.items():
                        # Determine the field key
                        if isinstance(field_spec, (MockVol.Required, MockVol.Optional)):
                            field_key = field_spec.key
                            is_required = isinstance(field_spec, MockVol.Required)
                        else:
                            # field_spec is the key itself
                            field_key = field_spec
                            is_required = False

                        print(f"  Checking field: {field_key}, required: {is_required}")

                        # Check if required field is present
                        if is_required and field_key not in data:
                            print(f"  ERROR: Missing required field {field_key}")
                            raise MockVol.Invalid(
                                f"Required field '{field_key}' not provided"
                            )

                        # Validate the value if present
                        if field_key in data:
                            value = data[field_key]
                            print(f"  Validating {field_key}={value} with {validator}")
                            # Call the validator if it's callable
                            if callable(validator):
                                try:
                                    result = validator(value)
                                    print(f"  Validation passed, result: {result}")
                                except MockVol.Invalid:
                                    raise
                                except Exception as e:
                                    print(f"  Validation failed: {e}")
                                    raise MockVol.Invalid(
                                        f"Invalid value for '{field_key}': {e}"
                                    )

                    print("  Validation successful")
                    return data

                def __init__(self, schema_dict):
                    self.schema_dict = schema_dict

            return SchemaValidator(schema_dict)

        @staticmethod
        def In(options):
            class InValidator:
                def __init__(self, options):
                    self.options = list(options) if options else []
                    print(f"Created InValidator with options: {self.options}")

                def __call__(self, value):
                    print(f"InValidator checking if '{value}' in {self.options}")
                    if value not in self.options:
                        raise MockVol.Invalid(
                            f"Invalid option: {value}, must be one of {self.options}"
                        )
                    return value

            return InValidator(options)

    vol_module = types.ModuleType("voluptuous")
    vol_module.Invalid = MockVol.Invalid
    vol_module.Required = MockVol.Required
    vol_module.Optional = MockVol.Optional
    vol_module.Schema = MockVol.Schema
    vol_module.In = MockVol.In
    sys.modules["voluptuous"] = vol_module

# Mock register constants - always force-set to ensure mock data is used
# even if another test file already populated sys.modules with real data
register_constants_module = types.ModuleType(
    "custom_components.ha_daikin_altherma4_modbus.register_constants"
)


class MockRegister:
    def __init__(self, register_name, enum_map=None, address=None):
        self.register_name = register_name
        self.enum_map = enum_map or {}
        self.address = address


class MockCalculatedRegister:
    def __init__(self, name, address, calc_type):
        self.name = name
        self.address = address
        self.calc_type = calc_type
        self.trigger_register_name = None


# Create mock holding registers with operation mode and Smart Grid registers
mock_operation_register = MockRegister("holding_3", {0: "off", 1: "heat", 2: "cool"})
mock_smart_grid_register = MockRegister(
    "holding_56",
    {
        0: "free_running",
        1: "forced_off",
        2: "recommended_on",
        3: "forced_on",
    },
)
register_constants_module.HOLDING_REGISTERS = [
    mock_operation_register,
    mock_smart_grid_register,
]
# Create mock coil registers for zone state tests
register_constants_module.COIL_REGISTERS = [
    MockRegister("coil_1", address=1),
    MockRegister("coil_2", address=2),
    MockRegister("coil_3", address=3),
]
register_constants_module.CALCULATED_SENSORS = [
    MockCalculatedRegister("test", 0, "simple")
]
register_constants_module.CALCULATED_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "calculated_sensors")}
}
register_constants_module.INPUT_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "input")}
}
register_constants_module.INPUT_REGISTERS = []
register_constants_module.DISCRETE_REGISTERS = []

sys.modules["custom_components.ha_daikin_altherma4_modbus.register_constants"] = (
    register_constants_module
)
sys.modules["custom_components.ha_daikin_altherma4_modbus.core.register_constants"] = (
    register_constants_module
)

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.ha]
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import ServiceCall, ServiceValidationError

# Force reload of services module to ensure it picks up the mocked HA modules
if "custom_components.ha_daikin_altherma4_modbus.integration.services" in sys.modules:
    del sys.modules["custom_components.ha_daikin_altherma4_modbus.integration.services"]

import custom_components.ha_daikin_altherma4_modbus.integration.services as services_module

importlib.reload(services_module)

from custom_components.ha_daikin_altherma4_modbus.core.const import (
    DOMAIN,
    HVAC_COOL,
    HVAC_HEAT,
    HVAC_OFF,
    SERVICE_REFRESH_CONNECTION,
    SERVICE_SET_ADDITIONAL_ZONE_SETPOINT,
    SERVICE_SET_ADDITIONAL_ZONE_STATE,
    SERVICE_SET_COOLING_OFFSET,
    SERVICE_SET_DHW_BOOSTER_MODE,
    SERVICE_SET_DHW_SINGLE_HEATUP,
    SERVICE_SET_DHW_STATE,
    SERVICE_SET_HEATING_OFFSET,
    SERVICE_SET_MAIN_ZONE_STATE,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_POWER_LIMIT,
    SERVICE_SET_QUIET_MODE,
    SERVICE_SET_ROOM_COOLING_SETPOINT,
    SERVICE_SET_ROOM_HEATING_SETPOINT,
    SERVICE_SET_SMART_GRID_MODE,
)
from custom_components.ha_daikin_altherma4_modbus.integration.services import (
    SERVICE_REFRESH_CONNECTION_SCHEMA,
    SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA,
    SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA,
    SERVICE_SET_COOLING_OFFSET_SCHEMA,
    SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA,
    SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA,
    SERVICE_SET_DHW_STATE_SCHEMA,
    SERVICE_SET_HEATING_OFFSET_SCHEMA,
    SERVICE_SET_MAIN_ZONE_STATE_SCHEMA,
    SERVICE_SET_OPERATION_MODE_SCHEMA,
    SERVICE_SET_POWER_LIMIT_SCHEMA,
    SERVICE_SET_QUIET_MODE_SCHEMA,
    SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA,
    SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA,
    SERVICE_SET_SMART_GRID_MODE_SCHEMA,
    async_set_additional_zone_state,
    async_set_dhw_state,
    async_set_main_zone_state,
    async_set_operation_mode,
    async_set_smart_grid_mode,
    get_operation_mode_map,
    get_smart_grid_mode_map,
)

# The stubs have served their purpose: everything this module needs from the
# stubbed modules has been imported above. Restore the original modules so
# that test modules collected after this one keep seeing the real
# implementation (see ``_STUB_MODULE_NAMES`` above).
_restore_stubbed_modules(_saved_sys_modules)


@pytest.fixture
def hass():
    """Create a Home Assistant fixture."""
    hass = MagicMock(spec=HomeAssistant)
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.state = "loaded"
    return entry


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    runtime_data = MagicMock()
    runtime_data.manager = AsyncMock()
    runtime_data.manager.write_holding_register = AsyncMock(return_value=True)
    runtime_data.manager.write_coil_register = AsyncMock(return_value=True)
    runtime_data.manager.host = "192.168.1.100"
    runtime_data.manager.port = 502
    return runtime_data


@pytest.fixture(autouse=True)
def reload_services_module():
    """Reload services module before each test to ensure fresh mocks.

    The stubbed modules are re-installed for the duration of each test and
    restored afterwards so they cannot leak into other test modules.
    """
    saved = {name: sys.modules.get(name, _MISSING) for name in _STUB_MODULE_NAMES}
    if _const_stub_installed:
        for name in (
            "custom_components.ha_daikin_altherma4_modbus.const",
            "custom_components.ha_daikin_altherma4_modbus.core.const",
        ):
            sys.modules[name] = const_module
    sys.modules["custom_components.ha_daikin_altherma4_modbus.register_constants"] = (
        register_constants_module
    )
    sys.modules[
        "custom_components.ha_daikin_altherma4_modbus.core.register_constants"
    ] = register_constants_module
    try:
        if (
            "custom_components.ha_daikin_altherma4_modbus.integration.services"
            in sys.modules
        ):
            del sys.modules[
                "custom_components.ha_daikin_altherma4_modbus.integration.services"
            ]
        import custom_components.ha_daikin_altherma4_modbus.integration.services as services_module

        importlib.reload(services_module)
        yield
    finally:
        _restore_stubbed_modules(saved)


class TestServiceSetup:
    """Test service setup and registration."""

    def test_async_setup_registers_services(self, hass):
        """Test that register_services registers services correctly."""
        from custom_components.ha_daikin_altherma4_modbus.integration.services import (
            register_services,
        )

        # Register services
        register_services(hass)

        assert hass.services.async_register.call_count == 15

        # Check service registration calls
        calls = hass.services.async_register.call_args_list

        # Expected services in order
        expected_services = [
            (SERVICE_SET_OPERATION_MODE, SERVICE_SET_OPERATION_MODE_SCHEMA),
            (SERVICE_SET_DHW_STATE, SERVICE_SET_DHW_STATE_SCHEMA),
            (SERVICE_SET_MAIN_ZONE_STATE, SERVICE_SET_MAIN_ZONE_STATE_SCHEMA),
            (
                SERVICE_SET_ADDITIONAL_ZONE_STATE,
                SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA,
            ),
            (SERVICE_SET_SMART_GRID_MODE, SERVICE_SET_SMART_GRID_MODE_SCHEMA),
            (SERVICE_SET_QUIET_MODE, SERVICE_SET_QUIET_MODE_SCHEMA),
            (SERVICE_SET_DHW_BOOSTER_MODE, SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA),
            (SERVICE_SET_DHW_SINGLE_HEATUP, SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA),
            (SERVICE_SET_POWER_LIMIT, SERVICE_SET_POWER_LIMIT_SCHEMA),
            (SERVICE_SET_HEATING_OFFSET, SERVICE_SET_HEATING_OFFSET_SCHEMA),
            (SERVICE_SET_COOLING_OFFSET, SERVICE_SET_COOLING_OFFSET_SCHEMA),
            (
                SERVICE_SET_ROOM_HEATING_SETPOINT,
                SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA,
            ),
            (
                SERVICE_SET_ROOM_COOLING_SETPOINT,
                SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA,
            ),
            (
                SERVICE_SET_ADDITIONAL_ZONE_SETPOINT,
                SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA,
            ),
            (SERVICE_REFRESH_CONNECTION, SERVICE_REFRESH_CONNECTION_SCHEMA),
        ]

        for i, (service_name, schema) in enumerate(expected_services):
            assert calls[i][0][0] == DOMAIN
            assert calls[i][0][1] == service_name
            # Schema comparison skipped due to object recreation on module reload


class TestSetOperationModeService:
    """Test set_operation_mode service."""

    async def test_set_operation_mode_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful operation mode setting."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_OPERATION_MODE,
            data={
                "config_entry_id": "test_entry_id",
                "operation_mode": "heat",
            },
        )

        # Execute service call
        await async_set_operation_mode(hass, call)

        # Verify the write was called
        operation_mode_map = get_operation_mode_map()
        mock_runtime_data.manager.write_holding_register.assert_called_once_with(
            "holding_3", operation_mode_map["heat"]
        )

    async def test_set_operation_mode_invalid_entry(self, hass):
        """Test service with invalid config entry."""

        # Setup
        hass.config_entries.async_get_entry.return_value = None

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_OPERATION_MODE,
            data={
                "config_entry_id": "invalid_entry_id",
                "operation_mode": "heat",
            },
        )

        # Execute and expect error
        with pytest.raises(
            ServiceValidationError,
        ):
            await async_set_operation_mode(hass, call)

    async def test_set_operation_mode_entry_not_loaded(self, hass, mock_config_entry):
        """Test service with entry not loaded."""

        # Setup
        mock_config_entry.state = "not_loaded"
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_OPERATION_MODE,
            data={
                "config_entry_id": "test_entry_id",
                "operation_mode": "heat",
            },
        )

        # Execute and expect error
        with pytest.raises(
            ServiceValidationError,
        ):
            await async_set_operation_mode(hass, call)

    async def test_set_operation_mode_invalid_mode(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test service with invalid operation mode."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call with invalid mode
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_OPERATION_MODE,
            data={
                "config_entry_id": "test_entry_id",
                "operation_mode": "invalid_mode",
            },
        )

        # Execute and expect error
        with pytest.raises(
            ServiceValidationError,
        ):
            await async_set_operation_mode(hass, call)


class TestSetDHWStateService:
    """Test set_dhw_state service."""

    async def test_set_dhw_state_on_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful DHW state set to on."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_DHW_STATE,
            data={
                "config_entry_id": "test_entry_id",
                "state": True,
            },
        )

        # Execute service call
        await async_set_dhw_state(hass, call)

        # Verify the write was called with coil_1 and True
        mock_runtime_data.manager.write_coil_register.assert_called_once_with(1, True)

    async def test_set_dhw_state_off_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful DHW state set to off."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_DHW_STATE,
            data={
                "config_entry_id": "test_entry_id",
                "state": False,
            },
        )

        # Execute service call
        await async_set_dhw_state(hass, call)

        # Verify the write was called with coil_1 and False
        mock_runtime_data.manager.write_coil_register.assert_called_once_with(1, False)

    async def test_set_dhw_state_invalid_entry(self, hass):
        """Test service with invalid config entry."""

        # Setup
        hass.config_entries.async_get_entry.return_value = None

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_DHW_STATE,
            data={
                "config_entry_id": "invalid_entry_id",
                "state": True,
            },
        )

        # Execute and expect error
        with pytest.raises(
            ServiceValidationError,
        ):
            await async_set_dhw_state(hass, call)


class TestSetMainZoneStateService:
    """Test set_main_zone_state service."""

    async def test_set_main_zone_state_on_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful main zone state set to on."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_MAIN_ZONE_STATE,
            data={
                "config_entry_id": "test_entry_id",
                "state": True,
            },
        )

        # Execute service call
        await async_set_main_zone_state(hass, call)

        # Verify the write was called with coil_2 and True
        mock_runtime_data.manager.write_coil_register.assert_called_once_with(2, True)

    async def test_set_main_zone_state_off_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful main zone state set to off."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_MAIN_ZONE_STATE,
            data={
                "config_entry_id": "test_entry_id",
                "state": False,
            },
        )

        # Execute service call
        await async_set_main_zone_state(hass, call)

        # Verify the write was called with coil_2 and False
        mock_runtime_data.manager.write_coil_register.assert_called_once_with(2, False)


class TestSetAdditionalZoneStateService:
    """Test set_additional_zone_state service."""

    async def test_set_additional_zone_state_on_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful additional zone state set to on."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_ADDITIONAL_ZONE_STATE,
            data={
                "config_entry_id": "test_entry_id",
                "state": True,
            },
        )

        # Execute service call
        await async_set_additional_zone_state(hass, call)

        # Verify the write was called with coil_3 and True
        mock_runtime_data.manager.write_coil_register.assert_called_once_with(3, True)

    async def test_set_additional_zone_state_off_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful additional zone state set to off."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_ADDITIONAL_ZONE_STATE,
            data={
                "config_entry_id": "test_entry_id",
                "state": False,
            },
        )

        # Execute service call
        await async_set_additional_zone_state(hass, call)

        # Verify the write was called with coil_3 and False
        mock_runtime_data.manager.write_coil_register.assert_called_once_with(3, False)


class TestServiceSchemas:
    """Test service validation schemas."""

    def test_set_operation_mode_schema_valid(self):
        """Test valid schema validation for set_operation_mode."""
        valid_data = {
            "config_entry_id": "test_entry_id",
            "operation_mode": "heat",
        }

        # Should not raise exception
        SERVICE_SET_OPERATION_MODE_SCHEMA(valid_data)

    def test_set_operation_mode_schema_invalid_mode(self):
        """Test invalid operation mode in schema."""
        invalid_data = {
            "config_entry_id": "test_entry_id",
            "operation_mode": "invalid_mode",
        }

        with pytest.raises(vol.Invalid):
            SERVICE_SET_OPERATION_MODE_SCHEMA(invalid_data)

    def test_set_operation_mode_schema_missing_required(self):
        """Test missing required fields in schema."""
        invalid_data = {
            "config_entry_id": "test_entry_id",
            # Missing operation_mode
        }

        with pytest.raises(vol.Invalid):
            SERVICE_SET_OPERATION_MODE_SCHEMA(invalid_data)

    def test_set_dhw_state_schema_valid(self):
        """Test valid schema validation for set_dhw_state."""
        valid_data = {
            "config_entry_id": "test_entry_id",
            "state": True,
        }

        # Should not raise exception
        SERVICE_SET_DHW_STATE_SCHEMA(valid_data)

    def test_set_dhw_state_schema_invalid_state(self):
        """Test invalid state in set_dhw_state schema."""
        invalid_data = {
            "config_entry_id": "test_entry_id",
            "state": "invalid",
        }

        with pytest.raises(vol.Invalid):
            SERVICE_SET_DHW_STATE_SCHEMA(invalid_data)

    def test_set_dhw_state_schema_missing_required(self):
        """Test missing required fields in set_dhw_state schema."""
        invalid_data = {
            # Missing config_entry_id and state
        }

        with pytest.raises(vol.Invalid):
            SERVICE_SET_DHW_STATE_SCHEMA(invalid_data)

    def test_set_main_zone_state_schema_valid(self):
        """Test valid schema validation for set_main_zone_state."""
        valid_data = {
            "config_entry_id": "test_entry_id",
            "state": True,
        }

        # Should not raise exception
        SERVICE_SET_MAIN_ZONE_STATE_SCHEMA(valid_data)

    def test_set_main_zone_state_schema_missing_required(self):
        """Test missing required fields in set_main_zone_state schema."""
        invalid_data = {
            "config_entry_id": "test_entry_id",
            # Missing state
        }

        with pytest.raises(vol.Invalid):
            SERVICE_SET_MAIN_ZONE_STATE_SCHEMA(invalid_data)

    def test_set_additional_zone_state_schema_valid(self):
        """Test valid schema validation for set_additional_zone_state."""
        valid_data = {
            "config_entry_id": "test_entry_id",
            "state": False,
        }

        # Should not raise exception
        SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA(valid_data)

    def test_set_additional_zone_state_schema_missing_required(self):
        """Test missing required fields in set_additional_zone_state schema."""
        invalid_data = {
            # Missing config_entry_id and state
        }

        with pytest.raises(vol.Invalid):
            SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA(invalid_data)


class TestSetSmartGridModeService:
    """Test set_smart_grid_mode service."""

    async def test_set_smart_grid_mode_success(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test successful Smart Grid mode setting."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_SMART_GRID_MODE,
            data={
                "config_entry_id": "test_entry_id",
                "smart_grid_mode": "recommended_on",
            },
        )

        # Execute service call
        await async_set_smart_grid_mode(hass, call)

        # Verify the write was called
        smart_grid_mode_map = get_smart_grid_mode_map()
        mock_runtime_data.manager.write_holding_register.assert_called_once_with(
            "holding_56", smart_grid_mode_map["recommended_on"]
        )

    async def test_set_smart_grid_mode_invalid_entry(self, hass):
        """Test service with invalid config entry."""

        # Setup
        hass.config_entries.async_get_entry.return_value = None

        # Create service call
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_SMART_GRID_MODE,
            data={
                "config_entry_id": "invalid_entry_id",
                "smart_grid_mode": "recommended_on",
            },
        )

        # Execute and expect error
        with pytest.raises(
            ServiceValidationError,
        ):
            await async_set_smart_grid_mode(hass, call)

    async def test_set_smart_grid_mode_invalid_mode(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test service with invalid Smart Grid mode."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call with invalid mode
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_SMART_GRID_MODE,
            data={
                "config_entry_id": "test_entry_id",
                "smart_grid_mode": "invalid_mode",
            },
        )

        # Execute and expect error
        with pytest.raises(
            ServiceValidationError,
        ):
            await async_set_smart_grid_mode(hass, call)


class TestServiceSchemasExtended:
    """Extended schema validation tests for all services."""

    def test_set_smart_grid_mode_schema_valid(self):
        """Test valid schema validation for set_smart_grid_mode."""
        valid_data = {
            "config_entry_id": "test_entry_id",
            "smart_grid_mode": "recommended_on",
        }

        # Should not raise exception
        SERVICE_SET_SMART_GRID_MODE_SCHEMA(valid_data)

    def test_set_smart_grid_mode_schema_invalid_mode(self):
        """Test invalid Smart Grid mode in schema."""
        invalid_data = {
            "config_entry_id": "test_entry_id",
            "smart_grid_mode": "invalid_mode",
        }

        with pytest.raises(vol.Invalid):
            SERVICE_SET_SMART_GRID_MODE_SCHEMA(invalid_data)

    async def test_set_smart_grid_mode_schema_missing_required(
        self, hass, mock_config_entry, mock_runtime_data
    ):
        """Test missing required fields in set_smart_grid_mode schema."""

        # Setup
        mock_config_entry.runtime_data = mock_runtime_data
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call with missing smart_grid_mode
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SET_SMART_GRID_MODE,
            data={
                "config_entry_id": "test_entry_id",
                # Missing smart_grid_mode
            },
        )

        # Execute and expect error (service handler validates required fields)
        with pytest.raises(
            ServiceValidationError,
        ):
            await async_set_smart_grid_mode(hass, call)


class TestOperationModeMapping:
    """Test operation mode mapping."""

    def test_operation_mode_mapping(self):
        """Test that operation mode mapping is correct."""
        operation_mode_map = get_operation_mode_map()
        assert operation_mode_map["off"] == HVAC_OFF
        assert operation_mode_map["heat"] == HVAC_HEAT
        assert operation_mode_map["cool"] == HVAC_COOL


class TestSmartGridModeMapping:
    """Test Smart Grid mode mapping."""

    def test_smart_grid_mode_mapping(self):
        """Test that Smart Grid mode mapping is correct."""
        smart_grid_mode_map = get_smart_grid_mode_map()
        assert smart_grid_mode_map["free_running"] == 0
        assert smart_grid_mode_map["forced_off"] == 1
        assert smart_grid_mode_map["recommended_on"] == 2
        assert smart_grid_mode_map["forced_on"] == 3
