"""Common patterns and utilities for Daikin Altherma 4 Modbus integration."""

from __future__ import annotations

import logging
from typing import Any, Dict, Union

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .data_types import EntityStatePayload, StateMapping

_LOGGER = logging.getLogger(__name__)


def get_coordinator_from_entry(hass: HomeAssistant, entry: ConfigType) -> Any:
    """Get coordinator from config entry runtime data."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator

    if coordinator is None:
        _LOGGER.error("Coordinator not found in runtime data")
        return None

    return coordinator


def validate_register_value(value: Any) -> bool:
    """Validate that a register value is available (not 32765 or 32766)."""
    if value is None:
        return False

    try:
        val = int(value)
    except (ValueError, TypeError):
        return False

    # Sensor is unavailable if value is 32765 or 32766
    return val not in [32765, 32766]


def is_unavailable_value(value: Any) -> bool:
    """Check if a register value indicates unavailability (32765 or 32766)."""
    if value is None:
        return True

    try:
        val = int(value)
    except (ValueError, TypeError):
        return True

    return val in [32765, 32766]


class BaseEntityMixin:
    """Common functionality for all Daikin entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        """Initialize base entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._entry = entry


def update_value_if_changed(
    unique_id: str,
    raw_value: Any,
    previous_data: StateMapping,
    register_type: str = "register",
    **kwargs,
) -> EntityStatePayload:
    """Update value if changed and return data dictionary.

    Args:
        unique_id: Unique identifier for the register
        raw_value: New value read from register
        previous_data: Previous cycle data
        register_type: Type description for logging
        **kwargs: Additional fields for the data dictionary (input_type, address, etc.)

    Returns:
        EntityStatePayload: Complete data payload for the register (new or unchanged)
    """
    # Get previous value
    prev_data = previous_data.get(unique_id)
    previous_value = prev_data.value if prev_data else None

    # Always update if no previous value exists
    if previous_value is None:
        _LOGGER.debug(f"{register_type} {unique_id} first read: {raw_value}")
        return EntityStatePayload(value=raw_value, **kwargs)

    # Check if value changed
    if raw_value != previous_value:
        _LOGGER.debug(
            f"{register_type} {unique_id} changed: {previous_value} -> {raw_value}"
        )
        return EntityStatePayload(value=raw_value, **kwargs)

    # Value unchanged - return previous data for this specific sensor
    _LOGGER.debug(f"{register_type} {unique_id} unchanged: {raw_value}")
    return prev_data


def get_register_value(data: Any) -> Any:
    """Get value from register data, supporting both dataclass and dictionary formats.

    Args:
        data: Register data (dataclass instance or dictionary)

    Returns:
        The value field or None if not found
    """
    if data is None:
        return None

    if hasattr(data, "value"):
        return data.value
    elif isinstance(data, dict):
        return data.get("value")
    else:
        return None


def get_register_scale(data: Any) -> Union[int, float]:
    """Get scale from register data, supporting both dataclass and dictionary formats.

    Args:
        data: Register data (dataclass instance or dictionary)

    Returns:
        The scale field or 1 if not found
    """
    if data is None:
        return 1

    if hasattr(data, "scale"):
        return data.scale
    elif isinstance(data, dict):
        return data.get("scale", 1)
    else:
        return 1


def is_entity_available(coordinator_data: dict, register_name: str) -> bool:
    """Check if an entity is available based on coordinator data.

    Args:
        coordinator_data: The coordinator's data dictionary
        register_name: The register name to check

    Returns:
        bool: True if entity is available, False otherwise
    """
    data = coordinator_data.get(register_name)
    val = get_register_value(data)
    return validate_register_value(val)


async def safe_write_register(
    write_func,
    register_name: str,
    value: Any,
    operation_name: str = "write",
    register_type: str = "register",
) -> None:
    """Safely write to a register with standardized error handling.

    Args:
        write_func: Async function to perform the write operation
        register_name: Name of the register being written
        value: Value to write
        operation_name: Description of the operation for logging (e.g., "turn on", "set temperature")
        register_type: Type of register for error messages

    Raises:
        HomeAssistantError: If the write operation fails
    """
    from homeassistant.exceptions import HomeAssistantError

    try:
        await write_func(register_name, value)
        _LOGGER.debug(f"Successfully {operation_name} {register_type} {register_name}")
    except (ValueError, ConnectionError) as e:
        _LOGGER.error(f"Error {operation_name} {register_type} {register_name}: {e}")
        raise HomeAssistantError(
            f"Failed to {operation_name} {register_type} {register_name}: {e}"
        ) from e
    except Exception as e:
        _LOGGER.error(f"Error {operation_name} {register_type} {register_name}: {e}")
        raise HomeAssistantError(
            f"Failed to {operation_name} {register_type} {register_name}"
        ) from e


def get_coordinator_register_data(
    coordinator: Any, register_name: str
) -> Dict[str, Any]:
    """Get register data from coordinator without DOMAIN prefix.

    Args:
        coordinator: The coordinator instance with data attribute
        register_name: The register name (may include DOMAIN prefix)

    Returns:
        Dict containing register data or empty dict if not found
    """
    # Optimize: Cache DOMAIN length to avoid repeated string operations
    domain_prefix_len = len(DOMAIN) + 1  # +1 for underscore
    if (
        len(register_name) > domain_prefix_len
        and register_name.startswith(DOMAIN)
        and register_name[len(DOMAIN)] == "_"
    ):
        address_name = register_name[domain_prefix_len:]
    else:
        address_name = register_name
    return coordinator.data.get(address_name, {})


def to_signed_16bit(value: int) -> int:
    """
    Convert unsigned 16-bit integer to signed integer.

    Args:
        value: Unsigned 16-bit integer (0-65535)

    Returns:
        Signed 16-bit integer (-32768 to 32767)

    Examples:
        >>> to_signed_16bit(65535)  # -1 in 2's complement
        -1
        >>> to_signed_16bit(32767)   # Maximum positive value
        32767
        >>> to_signed_16bit(32768)   # Minimum negative value
        -32768
    """
    if not (0 <= value <= 65535):
        _LOGGER.warning(f"Value {value} is outside 16-bit range (0-65535)")
        return value

    # If the most significant bit is set (value >= 32768), it's a negative number
    if value >= 32768:
        return value - 65536
    return value


def to_unsigned_16bit(value: int) -> int:
    """
    Convert signed integer to unsigned 16-bit integer.

    Args:
        value: Signed integer (-32768 to 32767)

    Returns:
        Unsigned 16-bit integer (0-65535)

    Examples:
        >>> to_unsigned_16bit(-1)     # 65535 in 2's complement
        65535
        >>> to_unsigned_16bit(32767)  # Maximum positive value
        32767
        >>> to_unsigned_16bit(-32768) # Minimum negative value
        32768
    """
    if not (-32768 <= value <= 32767):
        _LOGGER.warning(
            f"Value {value} is outside signed 16-bit range (-32768 to 32767)"
        )
        return value

    # For negative numbers, convert to 2's complement
    if value < 0:
        return value + 65536
    return value


def clamp_16bit(value: int) -> int:
    """
    Clamp value to valid 16-bit unsigned range.

    Args:
        value: Any integer

    Returns:
        Value clamped to 0-65535 range
    """
    return max(0, min(65535, value))
