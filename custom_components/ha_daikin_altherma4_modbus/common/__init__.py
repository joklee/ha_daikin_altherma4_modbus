"""Common utilities for Daikin Altherma 4 Modbus integration."""

from .helpers import (
    BaseEntityMixin,
    clamp_16bit,
    get_coordinator_from_entry,
    get_coordinator_register_data,
    get_register_config,
    get_register_scale,
    get_register_value,
    is_entity_available,
    is_unavailable_value,
    safe_write_register,
    to_signed_16bit,
    to_unsigned_16bit,
    update_value_if_changed,
    validate_register_value,
)

__all__ = [
    "BaseEntityMixin",
    "clamp_16bit",
    "get_coordinator_from_entry",
    "get_coordinator_register_data",
    "get_register_config",
    "get_register_scale",
    "get_register_value",
    "is_entity_available",
    "is_unavailable_value",
    "safe_write_register",
    "to_signed_16bit",
    "to_unsigned_16bit",
    "update_value_if_changed",
    "validate_register_value",
]
