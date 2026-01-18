from .const import DOMAIN
from .coordinator import DaikinAlthermaCoordinator

async def async_setup_entry(hass, entry):
    coordinator = DaikinAlthermaCoordinator(
        hass,
        entry.data["host"],
        entry.data["port"],
        entry.data["scan_interval"],
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor", "number"])
    return True
