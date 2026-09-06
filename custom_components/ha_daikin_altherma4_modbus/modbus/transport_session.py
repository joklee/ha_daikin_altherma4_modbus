"""Transport/session layer for Modbus connectivity."""

import logging
from typing import Any

from ..core.exceptions import DaikinModbusException
from .client_interface import ModbusClientInterface
from .connection_manager import (
    async_get_ha_unit,
    ensure_modbus_connection,
)

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
        # Connection identity handed down for the HA-backed provider
        # (used in Phase 3; optional so existing call sites keep working).
        self.hass = hass
        self.entry = entry
        self.unit_id = unit_id
        self.client: ModbusClientInterface | None = None

    @staticmethod
    def is_modbus_error(response) -> object | bool:
        """Check if a Modbus response indicates an error."""
        if hasattr(response, "isError") and callable(response.isError):
            return response.isError()
        if hasattr(response, "is_error") and callable(response.is_error):
            return response.is_error()
        return False

    async def ensure_connection(self) -> ModbusClientInterface | None:
        """Ensure we have an active client and return it.

        On the HA-backed path the unit is lazy (no I/O): the first read opens
        the shared connection and a dropped link reopens on the next request,
        so we never force a connect here. On the legacy path we fall through to
        the existing real/mock connection handling.
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

        if self.client is None:
            _LOGGER.debug("Creating Modbus client for %s:%s", self.host, self.port)

        try:
            self.client = await ensure_modbus_connection(
                self.client, self.host, self.port, self.demo_mode
            )
            return self.client
        except (DaikinModbusException, OSError, TimeoutError) as err:
            _LOGGER.error(
                "Failed to establish Modbus connection to %s:%s: %s",
                self.host,
                self.port,
                err,
            )

            if self.demo_mode:
                _LOGGER.info("In demo mode, creating mock client as fallback")
                from .mock_client import MockModbusTcpClient

                self.client = MockModbusTcpClient(self.host, self.port)
                try:
                    await self.client.connect()
                    _LOGGER.info(
                        "Successfully created fallback mock client in demo mode"
                    )
                    return self.client
                except (DaikinModbusException, OSError, TimeoutError) as mock_err:
                    _LOGGER.error("Even mock client creation failed: %s", mock_err)
                    self.client = None
                    return None

            _LOGGER.error("Real mode connection failed to %s:%s", self.host, self.port)
            _LOGGER.info("Possible solutions:")
            _LOGGER.info("1. Check if the Daikin device is powered on")
            _LOGGER.info("2. Verify the IP address and port (default: 502)")
            _LOGGER.info("3. Check network connectivity to the device")
            _LOGGER.info("4. Ensure Modbus TCP is enabled on the device")
            _LOGGER.info("5. Try enabling demo mode for testing")
            self.client = None
            return None
        except Exception:
            _LOGGER.exception(
                "Unexpected error while establishing Modbus connection to %s:%s",
                self.host,
                self.port,
            )
            raise

    async def reconnect_with_new_client(self) -> ModbusClientInterface | None:
        """(Re)obtain the client, forcing a fresh handle.

        On the HA-backed path this does not recreate the shared connection —
        ``async_get_unit`` returns the same shared unit — but it refreshes the
        facade handle. On the legacy path a new client is created.
        """
        self.client = await self._new_client()
        return self.client

    @property
    def _ha_backed(self) -> bool:
        """Whether this session should use the HA-backed provider."""
        return bool(self.hass is not None and self.entry is not None)

    async def _new_client(self) -> ModbusClientInterface:
        """Return a new client via the HA provider or the legacy path."""
        if self._ha_backed and not self.demo_mode:
            unit_id = self.unit_id if self.unit_id is not None else 1
            return await async_get_ha_unit(
                self.hass, self.entry, self.host, self.port, unit_id
            )
        return await ensure_modbus_connection(
            None, self.host, self.port, self.demo_mode
        )
