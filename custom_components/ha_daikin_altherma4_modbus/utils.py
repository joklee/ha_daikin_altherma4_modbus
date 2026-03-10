"""Utility functions for safe data conversions."""

import logging

_LOGGER = logging.getLogger(__name__)


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
