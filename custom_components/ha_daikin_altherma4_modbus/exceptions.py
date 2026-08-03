"""Custom exceptions for Daikin Altherma 4 Modbus integration."""

import logging

_LOGGER = logging.getLogger(__name__)


class DaikinModbusException(Exception):
    """Base exception for Daikin Modbus operations."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
        if original_error:
            _LOGGER.debug(
                f"Original error: {type(original_error).__name__}: {original_error}"
            )


class ModbusConnectionException(DaikinModbusException):
    """Exception raised when Modbus connection fails."""



class ModbusReadException(DaikinModbusException):
    """Exception raised when Modbus read operation fails."""



class ModbusWriteException(DaikinModbusException):
    """Exception raised when Modbus write operation fails."""



class ModbusTimeoutException(DaikinModbusException):
    """Exception raised when Modbus operation times out."""



class ModbusInvalidAddressException(DaikinModbusException):
    """Exception raised when invalid Modbus address is used."""



class ModbusDeviceException(DaikinModbusException):
    """Exception raised when Modbus device reports an error."""

