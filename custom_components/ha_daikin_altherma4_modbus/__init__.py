import logging
from .const import DOMAIN
from .coordinator import DaikinAlthermaCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    # Create dynamic device info with connection parameters
    host = entry.data["host"]
    port = entry.data["port"]
    scan_interval = entry.data["scan_interval"]
    
    # Create device info with connection parameters
    device_info = {
        "identifiers": {("daikin_altherma_modbus", "altherma_main")},
        "name": "Daikin Altherma 4",
        "manufacturer": "Daikin",
        "model": "EPSX",
        "configuration_url": f"http://{host}",
        "sw_version": f"Modbus TCP {host}:{port} (Interval: {scan_interval}s)",
    }
    
    # Store device info in hass data for platforms to use
    hass.data.setdefault(f"{DOMAIN}_device_info", {})[entry.entry_id] = device_info
    
    coordinator = DaikinAlthermaCoordinator(
        hass,
        host,
        port,
        scan_interval,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor", "number", "select", "climate"])
    return True


async def async_update_entry(hass, entry):
    """Handle config entry updates."""
    _LOGGER.info(f"=== async_update_entry called ===")
    _LOGGER.info(f"Updating entry. Current data: {entry.data}")
    _LOGGER.info(f"Entry options: {entry.options}")
    
    # Create new data dict with current data
    new_data = dict(entry.data)
    
    # Always check for electric_power_sensor key
    if "electric_power_sensor" in entry.options:
        # Key is explicitly set in options
        if entry.options["electric_power_sensor"]:
            new_data["electric_power_sensor"] = entry.options["electric_power_sensor"]
            _LOGGER.info(f"Setting electric_power_sensor to: {entry.options['electric_power_sensor']}")
        else:
            # Empty value means delete
            if "electric_power_sensor" in new_data:
                del new_data["electric_power_sensor"]
                _LOGGER.info("Removing electric_power_sensor from configuration (empty value)")
    else:
        # Key not in options means delete it
        if "electric_power_sensor" in new_data:
            del new_data["electric_power_sensor"]
            _LOGGER.info("Removing electric_power_sensor from configuration (not in options)")
    
    _LOGGER.info(f"New entry data will be: {new_data}")
    # Update the entry with new data
    hass.config_entries.async_update_entry(entry, data=new_data)
    
    _LOGGER.info("Reloading entry...")
    await hass.config_entries.async_reload(entry.entry_id)
    _LOGGER.info("=== async_update_entry completed ===")


async def async_unload_entry(hass, entry):
    """Handle config entry unload."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "binary_sensor", "number", "select", "climate"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Clean up device info
        if f"{DOMAIN}_device_info" in hass.data:
            hass.data[f"{DOMAIN}_device_info"].pop(entry.entry_id, None)
    return unload_ok
