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

INPUT_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "input_registers")},
    "translation_key": "daikin_altherma_modbus_input_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4",
}

HOLDING_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "holding_registers")},
    "translation_key": "daikin_altherma_modbus_holding_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4",
}

CALCULATED_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "calculated_sensors")},
    "translation_key": "daikin_altherma_modbus_calculated_sensors",
    "manufacturer": "Daikin",
    "model": "Altherma 4",
}

DISCRETE_INPUT_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "discrete_input_registers")},
    "translation_key": "daikin_altherma_modbus_discrete_input_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4",
}

COIL_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "coil_registers")},
    "translation_key": "daikin_altherma_modbus_coil_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4",
}

# Register constants for Daikin Altherma 4
REGISTER_OPERATION_MODE = "holding_3"  # Operation mode
REGISTER_CURRENT_TEMP = (
    "input_40"  # Leaving water temperature PHE (plate heat exchanger)
)
REGISTER_OFFSET_HEATING = (
    "holding_54"  # Weather-dependent mode Main LWT Heating setpoint offset
)
REGISTER_OFFSET_COOLING = (
    "holding_53"  # Weather-dependent mode Main LWT Cooling setpoint offset
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

# Import dataclass-based constants directly
# These replace the old dictionary-based constants
from .register_constants import (  # noqa: F401
    CALCULATED_SENSORS,
    COIL_REGISTERS,
    DISCRETE_INPUT_SENSORS,
    HOLDING_REGISTERS,
    HOLDING_SWITCHES,
    INPUT_REGISTERS,
    HOLDING_SELECT_REGISTERS,
)

# Alias for backward compatibility
COIL_REGISTERS = COIL_REGISTERS
