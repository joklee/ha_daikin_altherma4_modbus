"""Device info utilities for Daikin Altherma 4 Modbus integration."""
import logging

_LOGGER = logging.getLogger(__name__)

def get_device_info(hass, entry_id):
    """Get device info with connection parameters."""
    device_info_key = f"ha_daikin_altherma4_modbus_device_info"
    if device_info_key in hass.data and entry_id in hass.data[device_info_key]:
        return hass.data[device_info_key][entry_id]
    
    # Fallback to empty device info
    return {}
