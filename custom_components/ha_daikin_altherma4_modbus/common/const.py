"""Common constants for Daikin Altherma 4 Modbus integration."""

from __future__ import annotations

# Domain name for the integration
DOMAIN = "ha_daikin_altherma4_modbus"

# Special register values that indicate unavailability or error states
# These values are used to determine if a register value is valid/available.
# Single source of truth (see also core/const.py re-export).
# Primary check is always the raw 16-bit value; the scaled set is only a
# defensive guard for payloads that were already scaled (e.g. 32766 * 0.01).
SPECIAL_REGISTER_NOT_SUPPORTED = 32767  # Register not supported by device
SPECIAL_REGISTER_NOT_AVAILABLE = 32766  # Register not available in current configuration
SPECIAL_REGISTER_WAITING = 32765  # Waiting for value (not yet loaded)

SPECIAL_REGISTER_VALUES = frozenset(
    {
        SPECIAL_REGISTER_NOT_SUPPORTED,
        SPECIAL_REGISTER_NOT_AVAILABLE,
        SPECIAL_REGISTER_WAITING,
    }
)

# Scaled guard equivalents for 0.01-scaled types (Temp16/Pow16/Int16S100).
# Never written by mapping_transform (specials stay raw); only checked
# defensively downstream for legacy/cached/test payloads.
SCALED_SPECIAL_REGISTER_VALUES = frozenset({327.67, 327.66, 327.65})
