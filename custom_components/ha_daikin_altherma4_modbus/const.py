try:
    from homeassistant.const import EntityCategory
except ImportError:
    # Fallback for testing when homeassistant is not available
    class EntityCategory:
        DIAGNOSTIC = "diagnostic"


DOMAIN = "ha_daikin_altherma4_modbus"
DEFAULT_PORT = 502

SLOW_SCAN_INTERVAL = 30
NORMAL_SCAN_INTERVAL = 5

# Valid Modbus address ranges based on device documentation
MIN_MODBUS_ADDRESS = 1
MAX_MODBUS_ADDRESS = 87

# Register constants for Daikin Altherma 4
REGISTER_OPERATION_MODE = "holding_3"  # Operation mode
REGISTER_CURRENT_TEMP = (
    "input_40"  # Leaving water temperature PHE (plate heat exchanger)
)
REGISTER_OFFSET_HEATING = (
    "holding_54"  # Weather-dependent mode Main LWT Heating setpoint offset
)
REGISTER_OFFSET_COOLING = (
    "holding_55"  # Weather-dependent mode Main LWT Cooling setpoint offset
)

# Additional register constants for Daikin Altherma 4
REGISTER_QUIET_MODE = "holding_9"  # Quiet mode operation
REGISTER_COMPRESSOR = "input_31"  # Compressor status

# DHW Control constants
REGISTER_DHW_HVAC_MODE = "coil_1"  # Domestic Hot Water
REGISTER_DHW_SETPOINT = "holding_10"  # DHW Single heat-up setpoint (Manual)
REGISTER_DHW_RUNNING = "discrete_19"  # DHW running status
REGISTER_DHW_TEMP = "input_43"  # DHW temperature

# DHW Booster Control constants
REGISTER_DHW_BOOSTER_HVAC_MODE = "holding_13"  # Domestic Hot Water
REGISTER_DHW_BOOSTER_SETPOINT = "holding_14"  # DHW Single heat-up setpoint (Manual)
REGISTER_DHW_BOOSTER_RUNNING = "discrete_19"  # DHW running status
REGISTER_DHW_BOOSTER_TEMP = "input_43"  # DHW temperature

# Register constants for thermal heat output calculation
REGISTER_FLOW_RATE = "input_49"  # Flow rate in L/min
REGISTER_LEAVING_WATER_TEMP = "input_40"  # Leaving water temperature PHE
REGISTER_RETURN_WATER_TEMP = "input_42"  # Return water temperature
REGISTER_HEAT_PUMP_POWER = "input_51"  # Heat pump power consumption

# Fan mode constants (quiet mode)
FAN_OFF = "OFF"
FAN_AUTO = "Auto"
FAN_MANUAL = "Manual"
FAN_FAN_OFF = "Off"

# HVAC mode constants
HVAC_OFF = 0
HVAC_HEAT = 1
HVAC_COOL = 2

# DHW constants
DHW_OFF = False
DHW_ON = True

# Special Modbus register return values (Daikin HomeHub)
# These values are returned when reading a register as signed or unsigned 16-bit.
SPECIAL_REGISTER_NOT_SUPPORTED = 32767  # Device does not support the requested register
SPECIAL_REGISTER_NOT_AVAILABLE = (
    32766  # Register not available in current configuration
)
SPECIAL_REGISTER_WAITING = 32765  # Register value not yet loaded

# Set of all special/unavailable register values
SPECIAL_REGISTER_VALUES = frozenset(
    {
        SPECIAL_REGISTER_NOT_SUPPORTED,
        SPECIAL_REGISTER_NOT_AVAILABLE,
        SPECIAL_REGISTER_WAITING,
    }
)

# Service names
SERVICE_SET_OPERATION_MODE = "set_operation_mode"
SERVICE_SET_DHW_STATE = "set_dhw_state"
SERVICE_SET_MAIN_ZONE_STATE = "set_main_zone_state"
SERVICE_SET_ADDITIONAL_ZONE_STATE = "set_additional_zone_state"
SERVICE_SET_SMART_GRID_MODE = "set_smart_grid_mode"
SERVICE_SET_QUIET_MODE = "set_quiet_mode"
SERVICE_SET_DHW_BOOSTER_MODE = "set_dhw_booster_mode"
SERVICE_SET_DHW_SINGLE_HEATUP = "set_dhw_single_heatup"
SERVICE_SET_POWER_LIMIT = "set_power_limit"
SERVICE_SET_HEATING_OFFSET = "set_heating_offset"
SERVICE_SET_COOLING_OFFSET = "set_cooling_offset"
SERVICE_SET_ROOM_HEATING_SETPOINT = "set_room_heating_setpoint"
SERVICE_SET_ROOM_COOLING_SETPOINT = "set_room_cooling_setpoint"
SERVICE_SET_ADDITIONAL_ZONE_SETPOINT = "set_additional_zone_setpoint"
SERVICE_REFRESH_CONNECTION = "refresh_connection"
