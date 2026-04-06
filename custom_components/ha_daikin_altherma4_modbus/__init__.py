import logging

from .config_entry_utils import entry_data_value, entry_value
from .const import DOMAIN, NORMAL_SCAN_INTERVAL, SLOW_SCAN_INTERVAL
from .coordinator_manager import CoordinatorManager, UnifiedCoordinator
from .modbus_client import RealModbusTcpClient
from .runtime_data import RuntimeData

_LOGGER = logging.getLogger(__name__)


def _has_other_entry_for_endpoint(
    hass, current_entry_id: str, host: str, port: int
) -> bool:
    """Return True if another loaded entry uses the same host/port."""
    domain_entries = hass.config_entries.async_entries(DOMAIN)
    for entry in domain_entries:
        if entry.entry_id == current_entry_id:
            continue
        if hasattr(entry, "runtime_data") and entry.runtime_data:
            manager = entry.runtime_data.manager
            if manager and manager.host == host and manager.port == port:
                return True
    return False


async def async_setup_entry(hass, entry):
    """Set up config entry and roll back resources on partial failure."""
    host = entry_data_value(entry, "host", "")
    port = entry_data_value(entry, "port", 502)
    scan_interval = entry_value(entry, "scan_interval", NORMAL_SCAN_INTERVAL)
    slow_scan_interval = entry_value(entry, "slow_scan_interval", SLOW_SCAN_INTERVAL)
    demo_mode = entry_value(entry, "demo_mode", False)

    # Test connection before setting up (unless in demo mode)
    if not demo_mode:
        _LOGGER.debug(f"Testing connection during setup to {host}:{port}")
        try:
            client = await RealModbusTcpClient.create(host, port, timeout=10)
            await client.connect()
            if not client.connected:
                _LOGGER.error(f"Cannot connect to {host}:{port} during setup")
                await RealModbusTcpClient.async_close_cached_client(host, port)
                return False
            # Disconnect after test - coordinators will create their own connections
            await client.disconnect()
            _LOGGER.debug(f"Connection test successful during setup to {host}:{port}")
        except Exception as err:
            _LOGGER.error(
                f"Connection test failed during setup to {host}:{port}: {err}"
            )
            await RealModbusTcpClient.async_close_cached_client(host, port)
            return False

    manager = CoordinatorManager(
        hass, host, port, scan_interval, slow_scan_interval, demo_mode
    )
    normal_coordinator = manager.get_coordinator("normal")
    slow_coordinator = manager.get_coordinator("slow")
    unified_coordinator = UnifiedCoordinator(
        hass,
        manager,
        normal_coordinator,
        slow_coordinator,
    )
    platforms = ["sensor", "binary_sensor", "number", "select", "climate", "switch"]
    stored_entry = False

    try:
        await unified_coordinator.async_setup()
        await manager.async_setup()

        _LOGGER.debug(
            "Unified coordinator initialized with %d data points",
            len(unified_coordinator.data),
        )

        hass.data.setdefault(DOMAIN, {})

        # Store runtime data in ConfigEntry.runtime_data
        entry.runtime_data = RuntimeData(
            coordinator=unified_coordinator,
            normal_coordinator=normal_coordinator,
            slow_coordinator=slow_coordinator,
            manager=manager,
        )

        # Keep minimal data in hass.data for backward compatibility during transition
        hass.data[DOMAIN][entry.entry_id] = {
            "runtime_data": entry.runtime_data,
        }
        stored_entry = True

        await hass.config_entries.async_forward_entry_setups(entry, platforms)
        return True
    except Exception as err:
        _LOGGER.error("Failed to set up entry %s: %s", entry.entry_id, err)

        domain_data = hass.data.get(DOMAIN, {})
        shared_endpoint_in_use = _has_other_entry_for_endpoint(
            hass, entry.entry_id, host, port
        )

        if stored_entry:
            domain_data.pop(entry.entry_id, None)

        if hasattr(unified_coordinator, "async_shutdown"):
            try:
                await unified_coordinator.async_shutdown()
            except Exception as shutdown_err:
                _LOGGER.debug(
                    "Failed shutting down unified coordinator after setup failure: %s",
                    shutdown_err,
                )

        try:
            await manager.async_shutdown(disconnect_clients=not shared_endpoint_in_use)
        except Exception as shutdown_err:
            _LOGGER.debug(
                "Failed shutting down manager after setup failure: %s", shutdown_err
            )

        if not shared_endpoint_in_use:
            await RealModbusTcpClient.async_close_cached_client(host, port)

        if not domain_data and DOMAIN in hass.data:
            hass.data.pop(DOMAIN, None)

        return False


async def async_unload_entry(hass, entry):
    """Handle config entry unload and close connections before HA restart."""
    _LOGGER.info("Unloading entry %s - closing Modbus connections", entry.entry_id)

    # Get runtime data from config entry
    runtime_data = getattr(entry, "runtime_data", None)
    if not runtime_data:
        _LOGGER.warning("No runtime data found for entry %s", entry.entry_id)
        return False

    unified_coordinator = runtime_data.coordinator
    manager = runtime_data.manager

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"]
    )
    if not unload_ok:
        _LOGGER.warning("Failed to unload entry %s", entry.entry_id)
        return False

    if unified_coordinator and hasattr(unified_coordinator, "async_shutdown"):
        try:
            await unified_coordinator.async_shutdown()
        except Exception as shutdown_err:
            _LOGGER.debug(
                "Failed shutting down unified coordinator during unload: %s",
                shutdown_err,
            )

    host = entry_data_value(entry, "host", "")
    port = entry_data_value(entry, "port", 502)
    shared_endpoint_in_use = _has_other_entry_for_endpoint(
        hass, entry.entry_id, host, port
    )

    if manager:
        try:
            await manager.async_shutdown(disconnect_clients=not shared_endpoint_in_use)
        except Exception as shutdown_err:
            _LOGGER.debug(
                "Failed shutting down manager during unload: %s", shutdown_err
            )

    if not shared_endpoint_in_use:
        try:
            await RealModbusTcpClient.async_close_cached_client(host, port)
        except Exception as shutdown_err:
            _LOGGER.debug(
                "Failed closing cached client during unload: %s", shutdown_err
            )

    # Clean up hass.data
    domain_data = hass.data.get(DOMAIN, {})
    domain_data.pop(entry.entry_id, None)
    if not domain_data and DOMAIN in hass.data:
        hass.data.pop(DOMAIN, None)

    _LOGGER.info("Successfully unloaded entry %s", entry.entry_id)
    return True
