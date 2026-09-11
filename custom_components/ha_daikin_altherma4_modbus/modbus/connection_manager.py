"""Modbus client connection management for Daikin Altherma integration."""

import logging
from typing import Any

from ..core.exceptions import ModbusConnectionException, ModbusTimeoutException
from .client_interface import ModbusClientInterface
from .mock_client import MockModbusTcpClient
from .modbus_client import RealModbusTcpClient
from .modbus_connection_client import ModbusConnectionClient

try:
    from homeassistant.components.modbus import async_get_temporary_unit, async_get_unit
    from modbus_connection import ModbusTcpParams
except ImportError:  # pragma: no cover - HA component not available in tests
    async_get_temporary_unit = None  # type: ignore[assignment]
    async_get_unit = None  # type: ignore[assignment]
    ModbusTcpParams = None  # type: ignore[assignment]

# HA 2026.9 introduces the shared ``modbus`` provider helpers
# (``async_get_unit`` / ``async_get_temporary_unit``). Until the runtime is
# upgraded, they may be missing even when ``modbus_connection`` is installed;
# the provider layer below must degrade gracefully instead of failing at
# import time.
_HAS_SHARED_UNIT_PROVIDER = (
    async_get_unit is not None and async_get_temporary_unit is not None
)

_LOGGER = logging.getLogger(__name__)


async def async_get_ha_unit(
    hass: Any,
    entry: Any,
    host: str,
    port: int,
    unit_id: int,
) -> ModbusClientInterface:
    """Return a facade over the unit HA's ``modbus`` component hands out.

    Calls ``async_get_unit(hass, entry, ModbusTcpParams(host, port), unit_id)``
    (no I/O — the first read opens the shared connection) and wraps the
    returned ``ModbusUnit`` in a :class:`ModbusConnectionClient`.

    Raises ``HomeAssistantError`` if the device is already in use under
    different link settings.
    """
    if not _HAS_SHARED_UNIT_PROVIDER or ModbusTcpParams is None:
        raise ModbusConnectionException(
            f"HA modbus component not available for {host}:{port}"
        )
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=host, port=port),
        unit_id,
    )
    return ModbusConnectionClient(unit=unit)


async def async_test_connection_with_temporary_unit(
    hass: Any,
    host: str,
    port: int,
    unit_id: int = 1,
) -> tuple[bool, str | None]:
    """Test Modbus connection using HA's temporary unit.

    Uses ``async_get_temporary_unit`` (async context manager) to obtain a
    temporary unit for connection testing without a config entry. Performs
    a read to verify the device is responsive.

    Returns:
        Tuple of (success, error_message)
        - success: True if connection was successful
        - error_message: None if successful, otherwise the error description
    """
    try:
        if not _HAS_SHARED_UNIT_PROVIDER or ModbusTcpParams is None:
            raise ModbusConnectionException(
                f"HA modbus component not available for {host}:{port}"
            )

        _LOGGER.debug(f"Testing connection to {host}:{port} using temporary unit")
        async with async_get_temporary_unit(
            hass,
            ModbusTcpParams(host=host, port=port),
            unit_id,
        ) as unit:
            client = ModbusConnectionClient(unit=unit)
            # Try to read a basic register to verify device is responsive
            # Using input register 1 which should exist on most Modbus devices
            await client.read_input_registers(1, 1)
            _LOGGER.debug(f"Connection test successful to {host}:{port}")
            return True, None
    except Exception as err:
        _LOGGER.debug(f"Connection test failed to {host}:{port}: {err}")
        return False, "cannot_connect"


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
