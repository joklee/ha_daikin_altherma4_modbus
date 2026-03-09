"""Modbus client connection management for Daikin Altherma integration."""

import logging
from .mock_client import MockModbusTcpClient
from .modbus_client import RealModbusTcpClient
from .client_interface import ModbusClientInterface
from .exceptions import ModbusConnectionException, ModbusTimeoutException

_LOGGER = logging.getLogger(__name__)


async def connect_modbus_client(
    client: ModbusClientInterface,
    host: str,
    port: int,
    connection_type: str = "connection",
) -> None:
    """Connect or reconnect Modbus client with error handling.

    Args:
        client: Modbus client to connect (real or mock)
        host: Modbus server host
        port: Modbus server port
        connection_type: Type of connection for logging ("connection" or "reconnection")

    Raises:
        UpdateFailed: If connection fails
    """
    try:
        await client.connect()
        if not client.connected:
            _LOGGER.error(f"Modbus {connection_type} failed to {host}:{port}")
            raise ModbusConnectionException(
                f"Modbus Verbindung zu {host}:{port} fehlgeschlagen"
            )
        else:
            _LOGGER.debug(
                f"Successfully {'re' if connection_type == 'reconnection' else ''}connected to Modbus TCP server at {host}:{port}"
            )
    except ModbusConnectionException:
        # Re-raise our own exceptions
        raise
    except TimeoutError as e:
        _LOGGER.error(f"Timeout during Modbus {connection_type} to {host}:{port}: {e}")
        raise ModbusTimeoutException(f"Modbus Verbindung zu {host}:{port} timeout", e)
    except ConnectionRefusedError as e:
        _LOGGER.error(
            f"Connection refused during Modbus {connection_type} to {host}:{port}: {e}"
        )
        raise ModbusConnectionException(
            f"Modbus Verbindung zu {host}:{port} wurde abgelehnt", e
        )
    except OSError as e:
        _LOGGER.error(
            f"Network error during Modbus {connection_type} to {host}:{port}: {e}"
        )
        raise ModbusConnectionException(
            f"Netzwerkfehler bei Verbindung zu {host}:{port}", e
        )
    except Exception as e:
        _LOGGER.error(
            f"Unexpected exception during Modbus {connection_type} to {host}:{port}: {e}"
        )
        raise ModbusConnectionException(
            f"Modbus Verbindung zu {host}:{port} fehlgeschlagen: {e}", e
        )


async def ensure_modbus_connection(
    client: ModbusClientInterface | None, host: str, port: int, demo_mode: bool = False
) -> ModbusClientInterface:
    """Ensure Modbus connection is established and return client.

    Args:
        client: Existing Modbus client or None
        host: Modbus server host
        port: Modbus server port
        demo_mode: If True, use mock client

    Returns:
        Connected Modbus client (real or mock)

    Raises:
        UpdateFailed: If connection fails
    """
    if client is None:
        if demo_mode:
            _LOGGER.debug("Creating mock Modbus TCP client for demo mode")
            client = MockModbusTcpClient(host, port=port)
        else:
            _LOGGER.debug(f"Creating new Modbus TCP client for {host}:{port}")
            client = RealModbusTcpClient(host, port=port)

        _LOGGER.debug(f"Connecting to Modbus TCP server at {host}:{port}")
        await connect_modbus_client(client, host, port, "connection")
    else:
        # Check if existing client is still connected
        if not client.connected:
            _LOGGER.warning(
                f"Modbus client disconnected, attempting reconnection to {host}:{port}"
            )
            await connect_modbus_client(client, host, port, "reconnection")
        else:
            _LOGGER.debug(f"Modbus client already connected to {host}:{port}")

    return client
