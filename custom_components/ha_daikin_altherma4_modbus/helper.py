"""Helper functions for Daikin Altherma Modbus integration."""

import logging
import random
from datetime import timedelta


_LOGGER = logging.getLogger(__name__)


def add_jitter(base_interval: int) -> timedelta:
    """Add random jitter to prevent TCP bursts."""
    jitter_range = int(base_interval * 0.2)  # 20% jitter
    jitter = random.randint(-jitter_range, jitter_range)
    return timedelta(seconds=base_interval + jitter)


def update_value_if_changed(unique_id: str, raw_value, previous_data: dict, register_type: str = "register", **kwargs) -> dict:
    """Update value if changed and return data dictionary.
    
    Args:
        unique_id: Unique identifier for the register
        raw_value: New value read from register
        previous_data: Previous cycle data
        register_type: Type description for logging
        **kwargs: Additional fields for the data dictionary (input_type, address, etc.)
    
    Returns:
        dict: Complete data dictionary for the register (new or unchanged)
    """
    # Get previous value
    prev_data = previous_data.get(unique_id, {})
    previous_value = prev_data.get("value")
    
    # Always update if no previous value exists
    if previous_value is None:
        _LOGGER.debug(f"{register_type} {unique_id} first read: {raw_value}")
        return {
            "value": raw_value,
            **kwargs
        }
    
    # Check if value changed
    if raw_value != previous_value:
        _LOGGER.debug(f"{register_type} {unique_id} changed: {previous_value} -> {raw_value}")
        return {
            "value": raw_value,
            **kwargs
        }
    
    # Value unchanged - return previous data for this specific sensor
    _LOGGER.debug(f"{register_type} {unique_id} unchanged: {raw_value}")
    return prev_data
