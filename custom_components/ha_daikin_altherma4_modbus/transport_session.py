"""Transport/session layer for Modbus connectivity."""

import logging
from .connection_manager import ensure_modbus_connection
from .client_interface import ModbusClientInterface

_LOGGER = logging.getLogger(__name__)


class ModbusTransportSession:
    """Owns Modbus client lifecycle for a single endpoint."""

    def __init__(self, host: str, port: int, demo_mode: bool = False):
        self.host = host
        self.port = port
        self.demo_mode = demo_mode
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
        """Ensure we have an active client and return it."""
        if self.client is None:
            _LOGGER.debug("Creating Modbus client for %s:%s", self.host, self.port)

        try:
            self.client = await ensure_modbus_connection(
                self.client, self.host, self.port, self.demo_mode
            )
            return self.client
        except Exception as err:
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
                except Exception as mock_err:
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

    async def reconnect_with_new_client(self) -> ModbusClientInterface | None:
        """Force new client creation and reconnect."""
        self.client = await ensure_modbus_connection(
            None, self.host, self.port, self.demo_mode
        )
        return self.client
