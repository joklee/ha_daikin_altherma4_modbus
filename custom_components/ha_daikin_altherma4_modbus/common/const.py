"""Common constants for Daikin Altherma 4 Modbus integration."""

from __future__ import annotations

# Domain name for the integration
DOMAIN = "ha_daikin_altherma4_modbus"

# Special register values that indicate unavailability or error states
# These values are used to determine if a register value is valid/available
SPECIAL_REGISTER_VALUES = {
    32767,  # Register not supported by device
    32766,  # Register not available in current configuration
    32765,  # Waiting for value (not yet loaded)
}
