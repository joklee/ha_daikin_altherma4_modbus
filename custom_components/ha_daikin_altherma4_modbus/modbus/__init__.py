"""Modbus module for Daikin Altherma 4 Modbus integration."""

from .client_interface import ModbusClientInterface
from .connection_manager import connect_modbus_client, ensure_modbus_connection
from .mock_client import MockModbusTcpClient
from .modbus_client import RealModbusTcpClient
from .register_repository import ModbusRegisterRepository
from .transport_session import ModbusTransportSession

__all__ = [
    "MockModbusTcpClient",
    "ModbusClientInterface",
    "ModbusRegisterRepository",
    "ModbusTransportSession",
    "RealModbusTcpClient",
    "connect_modbus_client",
    "ensure_modbus_connection",
]
