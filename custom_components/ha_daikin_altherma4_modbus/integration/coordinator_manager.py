"""Coordinator manager to handle multiple coordinators with different intervals."""

import asyncio
import logging
from typing import Any

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..core.const import DOMAIN
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
        entry=None,
        unit_id: int | None = None,
    ):
        """Initialize the coordinator manager."""
        self.hass = hass
        self.host = host
        self.port = port
        self.demo_mode = demo_mode
        self.entry = entry
        self.unit_id = unit_id

        # Create coordinators
        self.normal_coordinator = DaikinAlthermaNormalCoordinator(
            hass, host, port, normal_interval, demo_mode, entry, unit_id
        )
        self.slow_coordinator = DaikinAlthermaSlowCoordinator(
            hass, host, port, slow_interval, demo_mode, entry, unit_id
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

    @staticmethod
    def _client_of(coordinator) -> Any | None:
        """Return the transport client of a coordinator, if any."""
        data_manager = getattr(coordinator, "data_manager", None)
        return getattr(data_manager, "client", None)

    @staticmethod
    def _latest(*values: float | None) -> float | None:
        """Return the newest timestamp, ignoring unset ones."""
        valid = [value for value in values if value is not None]
        return max(valid) if valid else None

    @property
    def connection_active(self) -> bool:
        """Whether any coordinator currently holds a connected client.

        This is shared-link state, not device health: the link can be up
        while the device stops answering. Prefer :meth:`device_reachable`
        as the user-facing health metric.
        """
        for coordinator in self.coordinators.values():
            client = self._client_of(coordinator)
            if client is not None and bool(getattr(client, "connected", False)):
                return True
        return False

    @property
    def device_reachable(self) -> bool:
        """Whether the device recently answered polls.

        Unlike :meth:`connection_active`, this reflects observed poll
        outcomes: reachable when at least one coordinator's last update
        succeeded without pending consecutive failures.
        """
        for coordinator in self.coordinators.values():
            last_ok = getattr(coordinator, "last_update_success", False) is True
            failures = int(getattr(coordinator, "_consecutive_failures", 0) or 0)
            if last_ok and failures == 0:
                return True
        return False

    @property
    def max_consecutive_failures(self) -> int:
        """Highest consecutive-failure count across coordinators.

        Mirrors the transient/persistent classification used for repair
        issues (see ``REPAIR_ISSUE_CONSECUTIVE_FAILURES``): 0 means
        healthy, higher values count down to a repair issue.
        """
        return max(
            (
                int(getattr(coordinator, "_consecutive_failures", 0) or 0)
                for coordinator in self.coordinators.values()
            ),
            default=0,
        )

    @property
    def last_read_at(self) -> float | None:
        """Epoch of the newest successful read across coordinators."""
        return self._latest(
            *(
                getattr(self._client_of(coordinator), "last_read_at", None)
                for coordinator in self.coordinators.values()
            )
        )

    @property
    def last_write_at(self) -> float | None:
        """Epoch of the newest successful write across coordinators."""
        return self._latest(
            *(
                getattr(self._client_of(coordinator), "last_write_at", None)
                for coordinator in self.coordinators.values()
            )
        )

    @staticmethod
    def _error_counts(coordinator, direction: str) -> dict[str, int]:
        """Return a client's error counters for one direction, if any."""
        client = CoordinatorManager._client_of(coordinator)
        counts = getattr(client, "error_counts", None)
        if not isinstance(counts, dict):
            return {}
        return {
            key: int(counts.get(f"{direction}_{key}", 0) or 0)
            for key in ("timeout", "connection", "invalid_address", "other")
        }

    def error_breakdown(self, direction: str) -> dict[str, int]:
        """Summed error counters for reads or writes across coordinators."""
        total = {"timeout": 0, "connection": 0, "invalid_address": 0, "other": 0}
        for coordinator in self.coordinators.values():
            for key, value in self._error_counts(coordinator, direction).items():
                total[key] += value
        return total

    @property
    def read_errors(self) -> int:
        """Total failed reads across coordinators."""
        return sum(self.error_breakdown("read").values())

    @property
    def write_errors(self) -> int:
        """Total failed writes across coordinators."""
        return sum(self.error_breakdown("write").values())

    @property
    def last_error_at(self) -> float | None:
        """Epoch of the newest failure across coordinators."""
        return self._latest(
            *(
                getattr(self._client_of(coordinator), "last_error_at", None)
                for coordinator in self.coordinators.values()
            )
        )

    @property
    def last_error(self) -> str | None:
        """Description of the newest failure across coordinators."""
        newest: float | None = None
        message: str | None = None
        for coordinator in self.coordinators.values():
            client = self._client_of(coordinator)
            stamp = getattr(client, "last_error_at", None)
            if stamp is not None and (newest is None or stamp > newest):
                newest = stamp
                text = getattr(client, "last_error", None)
                message = str(text) if text is not None else None
        return message

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

    async def refresh_connection(self) -> None:
        """Refresh the Modbus connection by reconnecting all coordinators."""
        _LOGGER.debug("Refreshing Modbus connection for all coordinators")
        try:
            # Refresh both coordinators' connections
            await self.normal_coordinator.data_manager.refresh_connection()
            await self.slow_coordinator.data_manager.refresh_connection()

            # Trigger data refresh after reconnection
            await self.async_request_refresh_all()

            _LOGGER.debug("Successfully refreshed Modbus connection")
        except Exception as err:
            _LOGGER.error("Failed to refresh Modbus connection: %s", err)
            raise


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
        self._refresh_tasks: set[asyncio.Task[Any]] = set()

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

        if self._refresh_tasks:
            for task in tuple(self._refresh_tasks):
                task.cancel()

            await asyncio.gather(*self._refresh_tasks, return_exceptions=True)
            self._refresh_tasks.clear()

    def _handle_source_coordinator_update(self) -> None:
        """Push merged data whenever one source coordinator updates."""
        self.async_set_updated_data(self.manager.get_all_data())

    def _handle_write_event(self, event: Event) -> None:
        """Handle write events by triggering refresh."""
        _LOGGER.debug(
            f"Write event received for register {event.data.get('register_name')}, "
            f"triggering automatic refresh"
        )
        # Track refresh tasks so they can be cancelled on unload.
        # Use call_soon_threadsafe to ensure async_create_task is called from the main loop
        self.hass.loop.call_soon_threadsafe(lambda: self._schedule_refresh_task())

    def _schedule_refresh_task(self) -> None:
        """Schedule refresh task from the main event loop."""
        if hasattr(self.hass, "async_create_task"):
            task = self.hass.async_create_task(self._async_refresh_after_write())
        else:
            task = asyncio.create_task(self._async_refresh_after_write())
        self._refresh_tasks.add(task)
        task.add_done_callback(self._refresh_tasks.discard)

    async def _async_refresh_after_write(self) -> None:
        """Refresh both source coordinators after write operation."""
        results = await asyncio.gather(
            self.slow_coordinator.async_request_refresh(),
            self.normal_coordinator.async_request_refresh(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("Post-write refresh failed: %s", result)

    async def _async_update_data(self):
        """Manual refresh path for user-triggered refreshes."""
        await self.manager.async_request_refresh_all()
        return self.manager.get_all_data()
