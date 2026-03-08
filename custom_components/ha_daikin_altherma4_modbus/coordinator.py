"""Simplified coordinator classes for Daikin Altherma 4 Modbus integration."""

import logging
import asyncio
from .retry_utils import add_jitter, DEFAULT_JITTER
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .data_manager import ModbusDataManager
from .const import DOMAIN
from .exceptions import (
    ModbusConnectionException,
    ModbusDeviceException,
    ModbusReadException,
    ModbusTimeoutException,
)

_LOGGER = logging.getLogger(__name__)
_COORDINATOR_IO_EXCEPTIONS = (
    ModbusReadException,
    ModbusTimeoutException,
    ModbusDeviceException,
    ModbusConnectionException,
    asyncio.TimeoutError,
    OSError,
    ConnectionError,
)


class DaikinAlthermaNormalCoordinator(DataUpdateCoordinator):
    """Normal interval coordinator for input and discrete registers."""

    def __init__(
        self,
        hass,
        host: str,
        port: int,
        scan_interval: int = 10,
        demo_mode: bool = False,
    ):
        # Add jitter to scan interval
        update_interval = add_jitter(scan_interval, DEFAULT_JITTER)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_normal",
            update_interval=update_interval,
        )
        _LOGGER.info(
            f"NormalCoordinator initialized with interval: {scan_interval}s (with jitter: {update_interval.total_seconds():.1f}s)"
        )
        self.host = host
        self.port = port
        self.demo_mode = demo_mode

        # Data manager for input/discrete registers
        self.data_manager = ModbusDataManager(host, port, demo_mode)

        self.data = {}

    async def _async_update_data(self):
        """Coordinate input and discrete input data fetching."""
        _LOGGER.debug("NormalCoordinator _async_update_data called")
        try:
            # Refresh input and discrete input data only
            input_data = await self.data_manager.fetch_input_registers_data()
            discrete_data = await self.data_manager.fetch_discrete_inputs_data()

            # Combine data
            self.data = {**input_data, **discrete_data}

            return self.data

        except _COORDINATOR_IO_EXCEPTIONS as err:
            _LOGGER.error(f"Error updating normal data: {err}")
            raise UpdateFailed(f"Error communicating with Modbus: {err}") from err


class DaikinAlthermaSlowCoordinator(DataUpdateCoordinator):
    """Slow interval coordinator for coil and holding registers."""

    def __init__(
        self,
        hass,
        host: str,
        port: int,
        scan_interval: int = 600,
        demo_mode: bool = False,
    ):
        # Add jitter to scan interval
        update_interval = add_jitter(scan_interval, DEFAULT_JITTER)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_slow",
            update_interval=update_interval,
        )
        _LOGGER.info(
            f"SlowCoordinator initialized with interval: {scan_interval}s (with jitter: {update_interval.total_seconds():.1f}s)"
        )
        self.host = host
        self.port = port
        self.demo_mode = demo_mode

        # Data manager for coil/holding registers
        self.data_manager = ModbusDataManager(host, port, demo_mode)

        self.data = {}

    async def _async_update_data(self):
        """Coordinate coil and holding register data fetching."""
        _LOGGER.debug("SlowCoordinator _async_update_data called")
        try:
            _LOGGER.debug("Updating slow data")
            # Refresh coil and holding register data only
            coil_data = await self.data_manager.refresh_coils()
            holding_data = await self.data_manager.refresh_holding_registers()

            # Combine data
            self.data = {**coil_data, **holding_data}

            return self.data

        except _COORDINATOR_IO_EXCEPTIONS as err:
            _LOGGER.error(f"Error updating slow data: {err}")
            raise UpdateFailed(f"Error communicating with Modbus: {err}") from err
