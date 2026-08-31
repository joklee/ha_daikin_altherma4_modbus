"""Test service actions for ha_daikin_altherma4_modbus integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import ServiceCall, ServiceValidationError

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
    entry.state = ConfigEntryState.LOADED
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


class TestServiceSetup:
    """Test service setup and registration."""

    def test_async_setup_registers_services(self, hass, monkeypatch):
        """Test that register_services registers services correctly."""
        # Ensure a fresh services module: a previous test module may have
        # patched integration.services in sys.modules (e.g. test_config_model
        # replaces register_services with a Mock), which would otherwise leave
        # HAS_HA in a stale/False state and skip registration entirely.
        import sys

        monkeypatch.delitem(
            sys.modules,
            "custom_components.ha_daikin_altherma4_modbus.integration.services",
            raising=False,
        )
        from custom_components.ha_daikin_altherma4_modbus.integration import (
            services as fresh_services,
        )

        assert fresh_services.HAS_HA, "expected real Home Assistant import"
        register_services = fresh_services.register_services
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
            hass=hass,
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
            hass=hass,
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
        mock_config_entry.state = ConfigEntryState.NOT_LOADED
        hass.config_entries.async_get_entry.return_value = mock_config_entry

        # Create service call
        call = ServiceCall(
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
            hass=hass,
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
