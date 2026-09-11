"""Modbus module for Daikin Altherma 4 Modbus integration."""

from .client_interface import ModbusClientInterface
from .connection_manager import (
    async_get_ha_unit,
    async_test_connection_with_temporary_unit,
    connect_modbus_client,
    ensure_modbus_connection,
)
from .mock_client import MockModbusTcpClient
from .modbus_client import RealModbusTcpClient
from .modbus_connection_client import ModbusConnectionClient
from .register_repository import ModbusRegisterRepository
from .transport_session import ModbusTransportSession

__all__ = [
    "MockModbusTcpClient",
    "ModbusClientInterface",
    "ModbusConnectionClient",
    "ModbusRegisterRepository",
    "ModbusTransportSession",
    "RealModbusTcpClient",
    "async_get_ha_unit",
    "async_test_connection_with_temporary_unit",
    "connect_modbus_client",
    "ensure_modbus_connection",
]
