"""Custom exceptions for Daikin Altherma 4 Modbus integration."""

import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class DaikinModbusException(Exception):
    """Base exception for Daikin Modbus operations."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error
        if original_error:
            _LOGGER.debug(
                f"Original error: {type(original_error).__name__}: {original_error}"
            )


class ModbusConnectionException(DaikinModbusException):
    """Exception raised when Modbus connection fails."""

    pass


class ModbusReadException(DaikinModbusException):
    """Exception raised when Modbus read operation fails."""

    pass


class ModbusWriteException(DaikinModbusException):
    """Exception raised when Modbus write operation fails."""

    pass


class ModbusTimeoutException(DaikinModbusException):
    """Exception raised when Modbus operation times out."""

    pass


class ModbusInvalidAddressException(DaikinModbusException):
    """Exception raised when invalid Modbus address is used."""

    pass


class ModbusDeviceException(DaikinModbusException):
    """Exception raised when Modbus device reports an error."""

    pass
