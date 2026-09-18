"""Modbus client connection management for Daikin Altherma integration.

Phase 5 of the ``modbus-connection`` migration: the only production paths
are the HA-backed shared unit (``async_get_ha_unit``), the temporary-unit
probe for flows/setup (``async_test_connection_with_temporary_unit``), and
the demo mock owned by :class:`ModbusTransportSession`. The legacy
``pymodbus``-direct client (``RealModbusTcpClient``,
``ensure_modbus_connection``, ``connect_modbus_client``) is removed — there
is no feature toggle and no fallback.
"""

import logging
from typing import Any

from ..core.exceptions import ModbusConnectionException
from .client_interface import ModbusClientInterface
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
