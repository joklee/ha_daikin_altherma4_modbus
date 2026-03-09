import logging
from .const import DOMAIN, SLOW_SCAN_INTERVAL, NORMAL_SCAN_INTERVAL
from .coordinator_manager import CoordinatorManager, UnifiedCoordinator
from .modbus_client import RealModbusTcpClient
from .config_entry_utils import entry_value, entry_data_value

_LOGGER = logging.getLogger(__name__)


def _has_other_entry_for_endpoint(
    domain_data: dict, current_entry_id: str, host: str, port: int
) -> bool:
    """Return True if another loaded entry uses the same host/port."""
    for entry_id, data in domain_data.items():
        if entry_id == current_entry_id:
            continue
        manager = data.get("manager")
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
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": unified_coordinator,
            "normal_coordinator": normal_coordinator,
            "slow_coordinator": slow_coordinator,
            "manager": manager,
        }
        stored_entry = True

        await hass.config_entries.async_forward_entry_setups(entry, platforms)
        return True
    except Exception as err:
        _LOGGER.error("Failed to set up entry %s: %s", entry.entry_id, err)

        domain_data = hass.data.get(DOMAIN, {})
        shared_endpoint_in_use = _has_other_entry_for_endpoint(
            domain_data, entry.entry_id, host, port
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

    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(entry.entry_id, {})
    unified_coordinator = entry_data.get("coordinator")
    manager = entry_data.get("manager")

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"]
    )
    if not unload_ok:
        _LOGGER.warning("Failed to unload entry %s", entry.entry_id)
        return False

    if unified_coordinator and hasattr(unified_coordinator, "async_shutdown"):
        await unified_coordinator.async_shutdown()

    host = entry_data_value(entry, "host", "")
    port = entry_data_value(entry, "port", 502)
    shared_endpoint_in_use = _has_other_entry_for_endpoint(
        domain_data, entry.entry_id, host, port
    )

    if manager:
        await manager.async_shutdown(disconnect_clients=not shared_endpoint_in_use)

    if not shared_endpoint_in_use:
        await RealModbusTcpClient.async_close_cached_client(host, port)

    domain_data.pop(entry.entry_id, None)
    _LOGGER.info("Successfully unloaded entry %s", entry.entry_id)

    if not domain_data and DOMAIN in hass.data:
        hass.data.pop(DOMAIN, None)

    return True
