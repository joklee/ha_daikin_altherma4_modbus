import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, SLOW_SCAN_INTERVAL, NORMAL_SCAN_INTERVAL
from .coordinator import DaikinAlthermaNormalCoordinator, DaikinAlthermaSlowCoordinator
from .coordinator_manager import CoordinatorManager
from .modbus_client import RealModbusTcpClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    # Create dynamic device info with connection parameters
    host = entry.data.get("host", "")
    port = entry.data.get("port", 502)
    scan_interval = entry.data.get("scan_interval", NORMAL_SCAN_INTERVAL)
    slow_scan_interval = entry.data.get("slow_scan_interval", SLOW_SCAN_INTERVAL)
    demo_mode = entry.data.get("demo_mode", False)
    
    # Create device info with connection parameters
    device_info = {
        "identifiers": {("daikin_altherma_modbus", "altherma_main")},
        "name": "Daikin Altherma 4",
        "manufacturer": "Daikin",
        "model": "EPSX",
        "configuration_url": f"http://{host}",
        "sw_version": f"Modbus TCP {host}:{port} (Interval: {scan_interval}s)" if not demo_mode else "Demo Mode",
    }

    # Create coordinator manager
    manager = CoordinatorManager(
        hass, host, port, scan_interval, slow_scan_interval, demo_mode
    )
    
    # Setup all coordinators
    await manager.async_setup()
    
    # Get individual coordinators
    normal_coordinator = manager.get_coordinator("normal")
    slow_coordinator = manager.get_coordinator("slow")

    # Create unified coordinator for backward compatibility
    class UnifiedCoordinator(DataUpdateCoordinator):
        def __init__(self, hass_instance, coord_manager):
            # Use a moderate interval since we just combine existing data
            update_interval = normal_coordinator.update_interval
            
            super().__init__(hass_instance, _LOGGER, name=f"{DOMAIN}_unified", update_interval=update_interval)
            _LOGGER.info(f"UnifiedCoordinator initialized with interval: {update_interval.total_seconds():.1f}s")
            self.manager = coord_manager
            self.normal_coordinator = normal_coordinator
            self.slow_coordinator = slow_coordinator
            self.data_manager = normal_coordinator.data_manager  # Use normal data_manager for writes
            self.data_manager.coordinator = self  # Set coordinator reference
            self.data = {}  # Initialize data attribute
            self._last_data_hash = None
        
        async def _async_update_data(self):
            # Combine data from all coordinators
            _LOGGER.debug("UnifiedCoordinator update called")
            
            # Get current data
            unified_data = self.manager.get_all_data()
            
            # Only update if data actually changed
            import hashlib
            import json
            current_hash = hashlib.md5(
                json.dumps(unified_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            
            if current_hash != self._last_data_hash:
                self.data = unified_data
                self._last_data_hash = current_hash
                _LOGGER.debug(f"UnifiedCoordinator data updated ({len(unified_data)} items)")
            else:
                _LOGGER.debug("UnifiedCoordinator data unchanged")
            
            return unified_data
    
    unified_coordinator = UnifiedCoordinator(hass, manager)

    # Initialize unified coordinator data
    unified_coordinator.data = manager.get_all_data()
    _LOGGER.debug(f"Unified coordinator initialized with {len(unified_coordinator.data)} data points")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": unified_coordinator,
        "normal_coordinator": normal_coordinator,
        "slow_coordinator": slow_coordinator,
        "manager": manager,
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"])
    return True


async def async_update_entry(hass, entry):
    """Handle config entry updates."""
    _LOGGER.debug(f"=== async_update_entry called ===")
    _LOGGER.debug(f"Updating entry. Current data: {entry.data}")
    _LOGGER.debug(f"Entry options: {entry.options}")
    
    # Create new data dict with current data
    new_data = dict(entry.data)
    
    # Update connection parameters if they changed
    if "host" in entry.options:
        new_data["host"] = entry.options["host"]
        _LOGGER.debug(f"Updated host to: {entry.options['host']}")
    
    if "port" in entry.options:
        new_data["port"] = entry.options["port"]
        _LOGGER.debug(f"Updated port to: {entry.options['port']}")
    
    if "scan_interval" in entry.options:
        new_data["scan_interval"] = entry.options["scan_interval"]
        _LOGGER.debug(f"Updated scan_interval to: {entry.options['scan_interval']}")
    
    # Update electric_power_sensor if present
    if "electric_power_sensor" in entry.options:
        if entry.options["electric_power_sensor"].strip():
            new_data["electric_power_sensor"] = entry.options["electric_power_sensor"].strip()
            _LOGGER.debug(f"Updated electric_power_sensor to: {entry.options['electric_power_sensor'].strip()}")
        else:
            if "electric_power_sensor" in new_data:
                del new_data["electric_power_sensor"]
                _LOGGER.debug("Removed electric_power_sensor")
    
    # Update demo_mode if present
    if "demo_mode" in entry.options:
        new_data["demo_mode"] = entry.options["demo_mode"]
        _LOGGER.debug(f"Updated demo_mode to: {entry.options['demo_mode']}")
    
    _LOGGER.debug(f"New entry data will be: {new_data}")
    # Update the entry with new data
    hass.config_entries.async_update_entry(entry, data=new_data)
    
    _LOGGER.debug("Reloading entry...")
    await hass.config_entries.async_reload(entry.entry_id)
    _LOGGER.debug("=== async_update_entry completed ===")

async def async_unload_entry(hass, entry):
    """Handle config entry unload and close connections before HA restart."""
    _LOGGER.info(f"Unloading entry {entry.entry_id} - closing Modbus connections")
    
    # Get manager and shutdown coordinators
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    manager = entry_data.get("manager")
    
    if manager:
        await manager.async_shutdown()
    
    # Close all Modbus connections
    RealModbusTcpClient.clear_cache()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "binary_sensor", "number", "select", "climate", "switch"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Clean up device info
        _LOGGER.info(f"Successfully unloaded entry {entry.entry_id}")
    else:
        _LOGGER.warning(f"Failed to unload entry {entry.entry_id}")
    
    return unload_ok
