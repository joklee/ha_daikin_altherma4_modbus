"""Services for Daikin Altherma 4 Modbus integration."""

import logging

try:
    import voluptuous as vol
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.helpers import config_validation as cv
    from homeassistant.helpers.service import async_register_admin_service

    HAS_HA = True
except ImportError:
    # Fallback for testing when homeassistant is not available
    HAS_HA = False

from .const import (
    DOMAIN,
    HVAC_COOL,
    HVAC_HEAT,
    HVAC_OFF,
    REGISTER_DHW_HVAC_MODE,
    REGISTER_OPERATION_MODE,
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
from .register_constants import COIL_REGISTERS, HOLDING_REGISTERS

_LOGGER = logging.getLogger(__name__)

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_OPERATION_MODE = "operation_mode"
ATTR_STATE = "state"
ATTR_SMART_GRID_MODE = "smart_grid_mode"
ATTR_QUIET_MODE = "quiet_mode"
ATTR_BOOSTER_MODE = "booster_mode"
ATTR_SINGLE_HEATUP = "single_heatup"
ATTR_SETPOINT = "setpoint"
ATTR_POWER_LIMIT = "power_limit"
ATTR_OFFSET = "offset"

# Operation mode mapping for service calls (lowercase keys for service API)
OPERATION_MODE_MAP = {
    "off": HVAC_OFF,
    "heat": HVAC_HEAT,
    "cool": HVAC_COOL,
}


# Smart Grid mode mapping for service calls (lowercase keys for service API)
def get_smart_grid_mode_map():
    """Get Smart Grid mode mapping from register constants."""
    # Find the Smart Grid register in HOLDING_REGISTERS
    for register in HOLDING_REGISTERS:
        if register.register_name == "holding_56":
            return {v.lower(): k for k, v in register.enum_map.items()}
    return {}


# Quiet mode mapping for service calls (lowercase keys for service API)
def get_quiet_mode_map():
    """Get Quiet mode mapping from register constants."""
    # Find the Quiet mode register in HOLDING_REGISTERS
    for register in HOLDING_REGISTERS:
        if register.register_name == "holding_9":
            return {v.lower(): k for k, v in register.enum_map.items()}
    return {}


# Service schemas (only defined when HA is available)
if HAS_HA:
    SERVICE_SET_OPERATION_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_OPERATION_MODE): vol.In(["off", "heat", "cool"]),
        }
    )

    SERVICE_SET_DHW_STATE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_STATE): cv.boolean,
        }
    )

    SERVICE_SET_MAIN_ZONE_STATE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_STATE): cv.boolean,
        }
    )

    SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_STATE): cv.boolean,
        }
    )

    # Get Smart Grid mode options from register constants
    smart_grid_options = list(get_smart_grid_mode_map().keys())
    SERVICE_SET_SMART_GRID_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SMART_GRID_MODE): vol.In(smart_grid_options),
        }
    )

    # Get Quiet mode options from register constants
    quiet_mode_options = list(get_quiet_mode_map().keys())
    SERVICE_SET_QUIET_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_QUIET_MODE): vol.In(quiet_mode_options),
        }
    )

    SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_BOOSTER_MODE): cv.boolean,
        }
    )

    SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SINGLE_HEATUP): cv.boolean,
            vol.Optional(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=30, max=85)
            ),
        }
    )

    SERVICE_SET_POWER_LIMIT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_POWER_LIMIT): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=20)
            ),
        }
    )

    SERVICE_SET_HEATING_OFFSET_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_OFFSET): vol.All(
                vol.Coerce(float), vol.Range(min=-10, max=10)
            ),
        }
    )

    SERVICE_SET_COOLING_OFFSET_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_OFFSET): vol.All(
                vol.Coerce(float), vol.Range(min=-10, max=10)
            ),
        }
    )

    SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=12, max=30)
            ),
        }
    )

    SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=12, max=35)
            ),
        }
    )

    SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=3, max=85)
            ),
        }
    )

    SERVICE_REFRESH_CONNECTION_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        }
    )
else:
    # Placeholders for testing - create dummy schemas that accept anything
    def _make_dummy_schema(fields):
        class DummySchema:
            def __call__(self, data):
                return data

        return DummySchema()

    SERVICE_SET_OPERATION_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_DHW_STATE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_MAIN_ZONE_STATE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_SMART_GRID_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_QUIET_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_POWER_LIMIT_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_HEATING_OFFSET_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_COOLING_OFFSET_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA = _make_dummy_schema(None)
    SERVICE_REFRESH_CONNECTION_SCHEMA = _make_dummy_schema(None)


def get_operation_mode_map():
    """Return the operation mode mapping."""
    return OPERATION_MODE_MAP.copy()


def _get_coil_address(register_name: str) -> int:
    """Get the coil address from register name."""
    for coil in COIL_REGISTERS:
        if coil.register_name == register_name:
            return coil.address
    raise ValueError(f"Coil register {register_name} not found")


if HAS_HA:

    def _get_entry_and_validate(hass, config_entry_id):
        """Get config entry and validate it's loaded."""
        entry = hass.config_entries.async_get_entry(config_entry_id)
        if entry is None:
            raise ServiceValidationError(
                f"Configuration entry {config_entry_id} not found"
            )
        if entry.state != ConfigEntryState.LOADED:
            raise ServiceValidationError(
                f"Configuration entry {config_entry_id} is not loaded"
            )
        return entry

    async def async_set_operation_mode(hass, call) -> None:
        """Set the heat pump operation mode."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        operation_mode = call.data[ATTR_OPERATION_MODE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        mode_value = OPERATION_MODE_MAP.get(operation_mode)
        if mode_value is None:
            raise ServiceValidationError(f"Invalid operation mode: {operation_mode}")

        await manager.write_holding_register(REGISTER_OPERATION_MODE, mode_value)
        _LOGGER.debug(
            "Set operation mode to %s (value: %s) for entry %s",
            operation_mode,
            mode_value,
            config_entry_id,
        )

    async def async_set_dhw_state(hass, call) -> None:
        """Enable or disable Domestic Hot Water."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        state = call.data[ATTR_STATE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        coil_address = _get_coil_address(REGISTER_DHW_HVAC_MODE)
        await manager.write_coil_register(coil_address, state)
        _LOGGER.debug(
            "Set DHW state to %s for entry %s",
            state,
            config_entry_id,
        )

    async def async_set_main_zone_state(hass, call) -> None:
        """Enable or disable the main zone."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        state = call.data[ATTR_STATE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Main zone is coil_2
        coil_address = _get_coil_address("coil_2")
        await manager.write_coil_register(coil_address, state)
        _LOGGER.debug(
            "Set main zone state to %s for entry %s",
            state,
            config_entry_id,
        )

    async def async_set_additional_zone_state(hass, call) -> None:
        """Enable or disable the additional zone."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        state = call.data[ATTR_STATE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Additional zone is coil_3
        coil_address = _get_coil_address("coil_3")
        await manager.write_coil_register(coil_address, state)
        _LOGGER.debug(
            "Set additional zone state to %s for entry %s",
            state,
            config_entry_id,
        )

    async def async_set_smart_grid_mode(hass, call) -> None:
        """Set the Smart Grid operation mode."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        smart_grid_mode = call.data[ATTR_SMART_GRID_MODE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        smart_grid_mode_map = get_smart_grid_mode_map()
        mode_value = smart_grid_mode_map.get(smart_grid_mode)
        if mode_value is None:
            raise ServiceValidationError(f"Invalid Smart Grid mode: {smart_grid_mode}")

        await manager.write_holding_register("holding_56", mode_value)
        _LOGGER.debug(
            "Set Smart Grid mode to %s (value: %s) for entry %s",
            smart_grid_mode,
            mode_value,
            config_entry_id,
        )

    async def async_set_quiet_mode(hass, call) -> None:
        """Set the Quiet mode operation."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        quiet_mode = call.data[ATTR_QUIET_MODE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        quiet_mode_map = get_quiet_mode_map()
        mode_value = quiet_mode_map.get(quiet_mode)
        if mode_value is None:
            raise ServiceValidationError(f"Invalid Quiet mode: {quiet_mode}")

        await manager.write_holding_register("holding_9", mode_value)
        _LOGGER.debug(
            "Set Quiet mode to %s (value: %s) for entry %s",
            quiet_mode,
            mode_value,
            config_entry_id,
        )

    async def async_set_dhw_booster_mode(hass, call) -> None:
        """Set the DHW booster mode."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        booster_mode = call.data[ATTR_BOOSTER_MODE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        await manager.write_holding_register("holding_13", 1 if booster_mode else 0)
        _LOGGER.debug(
            "Set DHW booster mode to %s for entry %s",
            booster_mode,
            config_entry_id,
        )

    async def async_set_dhw_single_heatup(hass, call) -> None:
        """Set the DHW single heat-up mode and optional setpoint."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        single_heatup = call.data[ATTR_SINGLE_HEATUP]
        setpoint = call.data.get(ATTR_SETPOINT)

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        await manager.write_holding_register("holding_15", 1 if single_heatup else 0)

        if setpoint is not None:
            # Convert setpoint to register value (scale by 0.01)
            register_value = int(setpoint / 0.01)
            await manager.write_holding_register("holding_16", register_value)
            _LOGGER.debug(
                "Set DHW single heat-up to %s with setpoint %s°C for entry %s",
                single_heatup,
                setpoint,
                config_entry_id,
            )
        else:
            _LOGGER.debug(
                "Set DHW single heat-up to %s for entry %s",
                single_heatup,
                config_entry_id,
            )

    async def async_set_power_limit(hass, call) -> None:
        """Set the imposed power limit."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        power_limit = call.data[ATTR_POWER_LIMIT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Convert power limit to register value (scale by 0.001)
        register_value = int(power_limit / 0.001)
        await manager.write_holding_register("holding_58", register_value)
        _LOGGER.debug(
            "Set power limit to %s kW (value: %s) for entry %s",
            power_limit,
            register_value,
            config_entry_id,
        )

    async def async_set_heating_offset(hass, call) -> None:
        """Set the weather-dependent heating offset."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        offset = call.data[ATTR_OFFSET]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Convert offset to register value (scale by 0.01)
        register_value = int(offset / 0.01)
        await manager.write_holding_register("holding_54", register_value)
        _LOGGER.debug(
            "Set heating offset to %s K (value: %s) for entry %s",
            offset,
            register_value,
            config_entry_id,
        )

    async def async_set_cooling_offset(hass, call) -> None:
        """Set the weather-dependent cooling offset."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        offset = call.data[ATTR_OFFSET]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Convert offset to register value (scale by 0.01)
        register_value = int(offset / 0.01)
        await manager.write_holding_register("holding_55", register_value)
        _LOGGER.debug(
            "Set cooling offset to %s K (value: %s) for entry %s",
            offset,
            register_value,
            config_entry_id,
        )

    async def async_set_room_heating_setpoint(hass, call) -> None:
        """Set the room thermostat heating setpoint."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        setpoint = call.data[ATTR_SETPOINT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Convert setpoint to register value (scale by 0.01)
        register_value = int(setpoint / 0.01)
        await manager.write_holding_register("holding_6", register_value)
        _LOGGER.debug(
            "Set room heating setpoint to %s°C (value: %s) for entry %s",
            setpoint,
            register_value,
            config_entry_id,
        )

    async def async_set_room_cooling_setpoint(hass, call) -> None:
        """Set the room thermostat cooling setpoint."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        setpoint = call.data[ATTR_SETPOINT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Convert setpoint to register value (scale by 0.01)
        register_value = int(setpoint / 0.01)
        await manager.write_holding_register("holding_7", register_value)
        _LOGGER.debug(
            "Set room cooling setpoint to %s°C (value: %s) for entry %s",
            setpoint,
            register_value,
            config_entry_id,
        )

    async def async_set_additional_zone_setpoint(hass, call) -> None:
        """Set the additional zone setpoint."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        setpoint = call.data[ATTR_SETPOINT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Convert setpoint to register value (scale by 0.01)
        register_value = int(setpoint / 0.01)
        await manager.write_holding_register("holding_63", register_value)
        _LOGGER.debug(
            "Set additional zone setpoint to %s°C (value: %s) for entry %s",
            setpoint,
            register_value,
            config_entry_id,
        )

    async def async_refresh_connection(hass, call) -> None:
        """Refresh the Modbus connection for the specified entry."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Trigger connection refresh by reconnecting
        await manager.refresh_connection()
        _LOGGER.debug(
            "Refreshed connection for entry %s",
            config_entry_id,
        )

else:
    # Dummy functions for testing imports
    async def async_set_operation_mode(hass, call):
        pass

    async def async_set_dhw_state(hass, call):
        pass

    async def async_set_main_zone_state(hass, call):
        pass

    async def async_set_additional_zone_state(hass, call):
        pass

    async def async_set_smart_grid_mode(hass, call):
        pass

    async def async_set_quiet_mode(hass, call):
        pass

    async def async_set_dhw_booster_mode(hass, call):
        pass

    async def async_set_dhw_single_heatup(hass, call):
        pass

    async def async_set_power_limit(hass, call):
        pass

    async def async_set_heating_offset(hass, call):
        pass

    async def async_set_cooling_offset(hass, call):
        pass

    async def async_set_room_heating_setpoint(hass, call):
        pass

    async def async_set_room_cooling_setpoint(hass, call):
        pass

    async def async_set_additional_zone_setpoint(hass, call):
        pass

    async def async_refresh_connection(hass, call):
        pass


def register_services(hass) -> None:
    """Register integration services."""
    if not HAS_HA:
        return
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_OPERATION_MODE,
        async_set_operation_mode,
        schema=SERVICE_SET_OPERATION_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_DHW_STATE,
        async_set_dhw_state,
        schema=SERVICE_SET_DHW_STATE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_MAIN_ZONE_STATE,
        async_set_main_zone_state,
        schema=SERVICE_SET_MAIN_ZONE_STATE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ADDITIONAL_ZONE_STATE,
        async_set_additional_zone_state,
        schema=SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_SMART_GRID_MODE,
        async_set_smart_grid_mode,
        schema=SERVICE_SET_SMART_GRID_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_QUIET_MODE,
        async_set_quiet_mode,
        schema=SERVICE_SET_QUIET_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_DHW_BOOSTER_MODE,
        async_set_dhw_booster_mode,
        schema=SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_DHW_SINGLE_HEATUP,
        async_set_dhw_single_heatup,
        schema=SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_POWER_LIMIT,
        async_set_power_limit,
        schema=SERVICE_SET_POWER_LIMIT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_HEATING_OFFSET,
        async_set_heating_offset,
        schema=SERVICE_SET_HEATING_OFFSET_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_COOLING_OFFSET,
        async_set_cooling_offset,
        schema=SERVICE_SET_COOLING_OFFSET_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ROOM_HEATING_SETPOINT,
        async_set_room_heating_setpoint,
        schema=SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ROOM_COOLING_SETPOINT,
        async_set_room_cooling_setpoint,
        schema=SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ADDITIONAL_ZONE_SETPOINT,
        async_set_additional_zone_setpoint,
        schema=SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_REFRESH_CONNECTION,
        async_refresh_connection,
        schema=SERVICE_REFRESH_CONNECTION_SCHEMA,
    )
    _LOGGER.debug("Registered Daikin Altherma 4 Modbus services")
