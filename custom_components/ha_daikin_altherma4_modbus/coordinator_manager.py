"""Coordinator manager to handle multiple coordinators with different intervals."""

import asyncio
import logging
from typing import Any
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN
from .coordinator import DaikinAlthermaNormalCoordinator, DaikinAlthermaSlowCoordinator

_LOGGER = logging.getLogger(__name__)


class CoordinatorManager:
    """Manages multiple coordinators and ensures they run independently."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        normal_interval: int = 10,
        slow_interval: int = 600,
        demo_mode: bool = False,
    ):
        """Initialize the coordinator manager."""
        self.hass = hass
        self.host = host
        self.port = port
        self.demo_mode = demo_mode

        # Create coordinators
        self.normal_coordinator = DaikinAlthermaNormalCoordinator(
            hass, host, port, normal_interval, demo_mode
        )
        self.slow_coordinator = DaikinAlthermaSlowCoordinator(
            hass, host, port, slow_interval, demo_mode
        )

        self.coordinators = {
            "normal": self.normal_coordinator,
            "slow": self.slow_coordinator,
        }

    async def async_setup(self):
        """Set up all coordinators using the normal DataUpdateCoordinator lifecycle."""
        _LOGGER.info("Setting up CoordinatorManager")

        for name, coordinator in self.coordinators.items():
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.info("%s coordinator first refresh completed", name)

        _LOGGER.info("CoordinatorManager setup completed")

    async def async_shutdown(self, disconnect_clients: bool = True):
        """Shutdown all coordinators and disconnect underlying clients."""
        _LOGGER.info("Shutting down CoordinatorManager")

        for name, coordinator in self.coordinators.items():
            try:
                if hasattr(coordinator, "async_shutdown"):
                    await coordinator.async_shutdown()

                data_manager = getattr(coordinator, "data_manager", None)
                client = getattr(data_manager, "client", None)

                if disconnect_clients and client is not None and client.connected:
                    await client.disconnect()

                _LOGGER.info("%s coordinator shutdown completed", name)
            except Exception as e:
                _LOGGER.warning("%s coordinator shutdown failed: %s", name, e)

    def get_coordinator(self, coordinator_type: str):
        """Get a specific coordinator by type."""
        return self.coordinators.get(coordinator_type)

    def get_all_data(self):
        """Get combined data from all coordinators."""
        combined_data = {}
        for coordinator in self.coordinators.values():
            if hasattr(coordinator, "data") and coordinator.data:
                combined_data.update(coordinator.data)
        return combined_data

    async def async_request_refresh_all(self) -> None:
        """Trigger refresh on all managed coordinators."""
        for coordinator in self.coordinators.values():
            await coordinator.async_request_refresh()


class UnifiedWriteProxy:
    """Write operations routed through source coordinators plus refresh."""

    def __init__(
        self,
        normal_coordinator: DaikinAlthermaNormalCoordinator,
        slow_coordinator: DaikinAlthermaSlowCoordinator,
    ):
        self._normal_coordinator = normal_coordinator
        self._slow_coordinator = slow_coordinator

    async def _async_fire_write_event(self, register_name: str, value: Any) -> None:
        """Fire domain event for write operations."""
        event_data = {
            "register_name": register_name,
            "value": value,
            "source": "write_operation",
        }

        # Fire domain event for automatic refresh
        self._normal_coordinator.hass.bus.async_fire(
            f"{DOMAIN}_register_written", event_data
        )

    async def _async_refresh_after_write(self) -> None:
        """Refresh both source coordinators without aborting on single failures."""
        results = await asyncio.gather(
            self._slow_coordinator.async_request_refresh(),
            self._normal_coordinator.async_request_refresh(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("Post-write refresh failed: %s", result)

    async def write_holding_register(self, register_name: str, value: int) -> Any:
        """Write a holding register and fire domain event."""
        result = await self._slow_coordinator.data_manager.write_holding_register(
            register_name, value
        )
        if result is not None:
            await self._async_fire_write_event(register_name, value)
        return result

    async def write_coil_register(self, register_name: str, value: bool) -> Any:
        """Write a coil register and refresh coordinators."""
        result = await self._slow_coordinator.data_manager.write_coil_register(
            register_name, value
        )
        if result is not None:
            await self._async_fire_write_event(register_name, value)
        return result


class UnifiedCoordinator(DataUpdateCoordinator):
    """Unified coordinator fed by normal and slow coordinators."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: CoordinatorManager,
        normal_coordinator: DaikinAlthermaNormalCoordinator,
        slow_coordinator: DaikinAlthermaSlowCoordinator,
    ):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_unified",
            update_interval=None,
        )
        self.manager = manager
        self.normal_coordinator = normal_coordinator
        self.slow_coordinator = slow_coordinator
        self.data_manager = UnifiedWriteProxy(normal_coordinator, slow_coordinator)
        self._unsubscribers: list = []

    async def async_setup(self) -> None:
        """Attach listeners to source coordinators and domain events."""
        # Listen to source coordinator updates
        self._unsubscribers.append(
            self.normal_coordinator.async_add_listener(
                self._handle_source_coordinator_update
            )
        )
        self._unsubscribers.append(
            self.slow_coordinator.async_add_listener(
                self._handle_source_coordinator_update
            )
        )

        # Listen to domain write events for automatic refresh
        self._unsubscribers.append(
            self.hass.bus.async_listen(
                f"{DOMAIN}_register_written", self._handle_write_event
            )
        )

    async def async_shutdown(self) -> None:
        """Detach source coordinator listeners."""
        while self._unsubscribers:
            unsubscribe = self._unsubscribers.pop()
            try:
                unsubscribe()
            except Exception as err:
                _LOGGER.debug("Failed to unsubscribe unified listener: %s", err)

    def _handle_source_coordinator_update(self) -> None:
        """Push merged data whenever one source coordinator updates."""
        self.async_set_updated_data(self.manager.get_all_data())

    def _handle_write_event(self, event: Event) -> None:
        """Handle write events by triggering refresh."""
        _LOGGER.debug(
            f"Write event received for register {event.data.get('register_name')}, "
            f"triggering automatic refresh"
        )
        # Trigger refresh after write operation
        asyncio.create_task(self._async_refresh_after_write())

    async def _async_refresh_after_write(self) -> None:
        """Refresh both source coordinators after write operation."""
        results = await asyncio.gather(
            self._slow_coordinator.async_request_refresh(),
            self._normal_coordinator.async_request_refresh(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("Post-write refresh failed: %s", result)

    async def _async_update_data(self):
        """Manual refresh path for user-triggered refreshes."""
        await self.manager.async_request_refresh_all()
        return self.manager.get_all_data()
