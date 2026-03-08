import logging
from .const import DOMAIN, SLOW_SCAN_INTERVAL, NORMAL_SCAN_INTERVAL
from .coordinator_manager import CoordinatorManager, UnifiedCoordinator
from .modbus_client import RealModbusTcpClient

_LOGGER = logging.getLogger(__name__)


def _entry_value(entry, key, default=None):
    """Read config from options first, then fallback to data."""
    options = getattr(entry, "options", {}) or {}
    data = getattr(entry, "data", {}) or {}
    return options.get(key, data.get(key, default))


def _entry_data_value(entry, key, default=None):
    """Read value from config entry data."""
    data = getattr(entry, "data", {}) or {}
    return data.get(key, default)


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
    # Create dynamic device info with connection parameters
    host = _entry_data_value(entry, "host", "")
    port = _entry_data_value(entry, "port", 502)
    scan_interval = _entry_value(entry, "scan_interval", NORMAL_SCAN_INTERVAL)
    slow_scan_interval = _entry_value(entry, "slow_scan_interval", SLOW_SCAN_INTERVAL)
    demo_mode = _entry_value(entry, "demo_mode", False)

    # Create device info with connection parameters

    # Create coordinator manager
    manager = CoordinatorManager(
        hass, host, port, scan_interval, slow_scan_interval, demo_mode
    )

    # Get individual coordinators
    normal_coordinator = manager.get_coordinator("normal")
    slow_coordinator = manager.get_coordinator("slow")

    unified_coordinator = UnifiedCoordinator(
        hass,
        manager,
        normal_coordinator,
        slow_coordinator,
    )
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

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"]
    )
    return True


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

    host = _entry_data_value(entry, "host", "")
    port = _entry_data_value(entry, "port", 502)
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
