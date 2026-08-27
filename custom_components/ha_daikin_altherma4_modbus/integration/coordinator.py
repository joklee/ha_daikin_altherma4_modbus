"""Simplified coordinator classes for Daikin Altherma 4 Modbus integration."""

import asyncio
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..core.const import DOMAIN, NORMAL_SCAN_INTERVAL, SLOW_SCAN_INTERVAL
from ..core.data_manager import ModbusDataManager
from ..core.exceptions import (
    ModbusConnectionException,
    ModbusDeviceException,
    ModbusReadException,
    ModbusTimeoutException,
)
from ..core.retry_utils import DEFAULT_JITTER, add_jitter
from .repair import async_create_connection_issue, async_delete_connection_issue

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
        scan_interval: int = NORMAL_SCAN_INTERVAL,
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
        self._connection_issue_created = False

    def _find_config_entry(self):
        """Find the config entry for this coordinator."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if (
                hasattr(entry, "runtime_data")
                and entry.runtime_data
                and entry.runtime_data.normal_coordinator is self
            ):
                return entry
        return None

    async def _async_update_data(self):
        """Coordinate input and discrete input data fetching."""
        _LOGGER.debug("NormalCoordinator _async_update_data called")
        try:
            # Refresh input and discrete input data only
            input_data = await self.data_manager.fetch_input_registers_data()
            discrete_data = await self.data_manager.fetch_discrete_inputs_data()

            # Combine data
            self.data = {**input_data, **discrete_data}

            # Connection recovered - delete repair issue if one was created
            if self._connection_issue_created:
                entry = self._find_config_entry()
                if entry:
                    async_delete_connection_issue(self.hass, entry)
                self._connection_issue_created = False

            return self.data

        except _COORDINATOR_IO_EXCEPTIONS as err:
            _LOGGER.error(f"Error updating normal data: {err}")
            # Create repair issue on connection failure
            if not self._connection_issue_created:
                entry = self._find_config_entry()
                if entry:
                    async_create_connection_issue(
                        self.hass, entry, f"Polling failed: {err}"
                    )
                    self._connection_issue_created = True
            raise UpdateFailed(f"Error communicating with Modbus: {err}") from err


class DaikinAlthermaSlowCoordinator(DataUpdateCoordinator):
    """Slow interval coordinator for coil and holding registers."""

    def __init__(
        self,
        hass,
        host: str,
        port: int,
        scan_interval: int = SLOW_SCAN_INTERVAL,
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
        self._connection_issue_created = False

    def _find_config_entry(self):
        """Find the config entry for this coordinator."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if (
                hasattr(entry, "runtime_data")
                and entry.runtime_data
                and entry.runtime_data.slow_coordinator is self
            ):
                return entry
        return None

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

            # Connection recovered - delete repair issue if one was created
            if self._connection_issue_created:
                entry = self._find_config_entry()
                if entry:
                    async_delete_connection_issue(self.hass, entry)
                self._connection_issue_created = False

            return self.data

        except _COORDINATOR_IO_EXCEPTIONS as err:
            _LOGGER.error(f"Error updating slow data: {err}")
            # Create repair issue on connection failure (only if not already created by normal coordinator)
            if not self._connection_issue_created:
                entry = self._find_config_entry()
                if entry:
                    # Only create if no issue exists yet (normal coordinator may have created one)
                    from .repair import ISSUE_CONNECTION_LOST

                    issue_id = f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}"
                    from homeassistant.helpers.issue_registry import (
                        async_get as async_get_issue_registry,
                    )

                    issue_registry = async_get_issue_registry(self.hass)
                    if issue_id not in issue_registry.issues:
                        async_create_connection_issue(
                            self.hass, entry, f"Polling failed: {err}"
                        )
                    self._connection_issue_created = True
            raise UpdateFailed(f"Error communicating with Modbus: {err}") from err
