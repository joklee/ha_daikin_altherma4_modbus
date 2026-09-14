"""Transport/session layer for Modbus connectivity.

Phase 5 of the ``modbus-connection`` migration: the session owns exactly one
client handle per endpoint, obtained from either the HA-backed shared unit
(``async_get_ha_unit`` — the production default, lazy, no I/O) or the demo
mock. There is no ``pymodbus``-direct fallback; real mode without
``hass``/``entry`` raises ``ModbusConnectionException`` instead of opening
an own connection.
"""

import logging
from typing import Any

from ..core.exceptions import DaikinModbusException, ModbusConnectionException
from .client_interface import ModbusClientInterface
from .connection_manager import async_get_ha_unit
from .mock_client import MockModbusTcpClient

_LOGGER = logging.getLogger(__name__)


class ModbusTransportSession:
    """Owns Modbus client lifecycle for a single endpoint."""

    def __init__(
        self,
        host: str,
        port: int,
        demo_mode: bool = False,
        hass: Any | None = None,
        entry: Any | None = None,
        unit_id: int | None = None,
    ):
        self.host = host
        self.port = port
        self.demo_mode = demo_mode
        # Connection identity for the HA-backed provider (the default path;
        # optional so demo/test call sites keep working).
        self.hass = hass
        self.entry = entry
        self.unit_id = unit_id
        self.client: ModbusClientInterface | None = None

    @staticmethod
    def is_modbus_error(response) -> object | bool:
        """Check if a Modbus response indicates an error.

        Demo/test-fake compat: the demo ``MockModbusTcpClient`` (and test
        fakes) return response objects with ``isError()`` / ``is_error()``.
        Flat ``list`` unit reads from ``ModbusConnectionClient`` never carry
        an error state — failures raise at the facade boundary — and are
        always classified as success.
        """
        if response is None or isinstance(response, (list, tuple)):
            return False
        if hasattr(response, "isError") and callable(response.isError):
            return response.isError()
        if hasattr(response, "is_error") and callable(response.is_error):
            return response.is_error()
        return False

    async def ensure_connection(self) -> ModbusClientInterface | None:
        """Ensure we have an active client and return it.

        On the HA-backed path the unit is lazy (no I/O): the first read opens
        the shared connection and a dropped link reopens on the next request,
        so we never force a connect here. Demo mode connects the mock.
        """
        if self.client is not None:
            return self.client

        if self._ha_backed:
            _LOGGER.debug(
                "Obtaining HA-backed Modbus unit for %s:%s (unit %s)",
                self.host,
                self.port,
                self.unit_id,
            )
            try:
                self.client = await self._new_client()
            except Exception:
                _LOGGER.exception(
                    "Unexpected error while obtaining HA-backed unit for %s:%s",
                    self.host,
                    self.port,
                )
                raise
            return self.client

        if self.demo_mode:
            _LOGGER.debug(
                "Creating mock Modbus client for demo mode at %s:%s",
                self.host,
                self.port,
            )
            try:
                self.client = await self._new_client()
                return self.client
            except (DaikinModbusException, OSError, TimeoutError) as err:
                _LOGGER.error(
                    "Failed to create mock Modbus client for %s:%s: %s",
                    self.host,
                    self.port,
                    err,
                )
                self.client = None
                return None
            except Exception:
                _LOGGER.exception(
                    "Unexpected error while creating mock Modbus client for %s:%s",
                    self.host,
                    self.port,
                )
                raise

        raise ModbusConnectionException(
            f"No HA-backed Modbus unit available for {self.host}:{self.port} "
            "(real mode requires hass/entry via the HA 2026.9 modbus component; "
            "use demo mode for testing without a device)"
        )

    async def reconnect_with_new_client(self) -> ModbusClientInterface | None:
        """(Re)obtain the client, forcing a fresh handle.

        On the HA-backed path this does not recreate the shared connection —
        ``async_get_unit`` returns the same shared unit — but it refreshes the
        facade handle. Demo mode reconnects a fresh mock.
        """
        self.client = await self._new_client()
        return self.client

    @property
    def _ha_backed(self) -> bool:
        """Whether this session should use the HA-backed provider."""
        return bool(
            self.hass is not None and self.entry is not None and not self.demo_mode
        )

    async def _new_client(self) -> ModbusClientInterface:
        """Return a new client via the HA provider or the demo mock."""
        if self._ha_backed:
            unit_id = self.unit_id if self.unit_id is not None else 1
            return await async_get_ha_unit(
                self.hass, self.entry, self.host, self.port, unit_id
            )
        if self.demo_mode:
            client: ModbusClientInterface = MockModbusTcpClient(self.host, self.port)
            await client.connect()
            if not client.connected:
                raise ModbusConnectionException(
                    f"Mock Modbus client failed to connect to {self.host}:{self.port}"
                )
            return client
        raise ModbusConnectionException(
            f"No HA-backed Modbus unit available for {self.host}:{self.port} "
            "(real mode requires hass/entry via the HA 2026.9 modbus component; "
            "use demo mode for testing without a device)"
        )
