import logging

from homeassistant.exceptions import ConfigEntryNotReady

from .config_flow import ConfigFlow as ConfigFlow
from .core.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    DEFAULT_UNIT_ID,
    DOMAIN,
    NORMAL_SCAN_INTERVAL,
    SLOW_SCAN_INTERVAL,
)
from .integration.config_entry_utils import entry_data_value, entry_value
from .integration.coordinator_manager import CoordinatorManager, UnifiedCoordinator
from .integration.repair import (
    async_create_connection_issue,
    async_delete_connection_issue,
)
from .integration.runtime_data import RuntimeData
from .integration.services import register_services

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass, entry):
    """Migrate a stored config entry to a newer version.

    Version 2 introduces the Modbus unit id (``unit_id``) to the entry
    ``data`` and includes it in the ``unique_id`` (``host:port:unit_id``).
    Old version-1 entries receive the default unit id (1) while every
    other value is preserved, so no reconfiguration is required.
    The function is idempotent: calling it again on an already-migrated
    entry is a no-op.
    """
    if entry.version < 2:
        data = {**entry.data}
        data.setdefault(CONF_UNIT_ID, DEFAULT_UNIT_ID)
        updates: dict = {"data": data, "version": 2}
        # Rewrite old-style unique_ids ("host:port") so the same triple
        # keeps matching after the scheme change. Anything else (already
        # new-style, None, custom) is left untouched.
        host = data.get(CONF_HOST)
        port = data.get(CONF_PORT)
        if (
            host is not None
            and port is not None
            and entry.unique_id == f"{host}:{port}"
        ):
            updates["unique_id"] = f"{host}:{port}:{data[CONF_UNIT_ID]}"
        hass.config_entries.async_update_entry(entry, **updates)
    return True


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
        unit_id = entry_data_value(entry, CONF_UNIT_ID, DEFAULT_UNIT_ID)
        try:
            # Local import: same helper the config/repair flows use, so the
            # real-HA tests can stub one seam (config_flow._test_connection).
            from .integration.config_flow import _test_connection

            connection_ok, _error_key = await _test_connection(
                hass, host, port, unit_id
            )
            if not connection_ok:
                _LOGGER.error(f"Cannot connect to {host}:{port} during setup")
                async_create_connection_issue(
                    hass, entry, f"Cannot connect to {host}:{port}"
                )
                raise ConfigEntryNotReady(f"Cannot connect to {host}:{port}")
            _LOGGER.debug(f"Connection test successful during setup to {host}:{port}")
        except ConfigEntryNotReady:
            raise
        except Exception as err:
            _LOGGER.error(
                f"Connection test failed during setup to {host}:{port}: {err}"
            )
            async_create_connection_issue(
                hass, entry, f"Connection failed to {host}:{port}"
            )
            raise ConfigEntryNotReady(f"Connection failed to {host}:{port}") from err
    unit_id = entry_data_value(entry, CONF_UNIT_ID, DEFAULT_UNIT_ID)

    manager = CoordinatorManager(
        hass,
        host,
        port,
        scan_interval,
        slow_scan_interval,
        demo_mode,
        entry,
        unit_id,
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

        # Register integration services
        register_services(hass)

        # Connection is healthy - delete any existing connection repair issue
        async_delete_connection_issue(hass, entry)

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

        if not domain_data and DOMAIN in hass.data:
            hass.data.pop(DOMAIN, None)

        raise ConfigEntryNotReady(f"Failed to set up entry: {err}") from err


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

    # Clean up hass.data
    domain_data = hass.data.get(DOMAIN, {})
    domain_data.pop(entry.entry_id, None)
    if not domain_data and DOMAIN in hass.data:
        hass.data.pop(DOMAIN, None)

    _LOGGER.info("Successfully unloaded entry %s", entry.entry_id)
    return True
