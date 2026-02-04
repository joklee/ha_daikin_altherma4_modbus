"""Switch platform for Daikin Altherma 4 Modbus integration."""
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, COIL_SENSORS, COIL_DEVICE_INFO

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup switch entities over Config Entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    # Coil Switches
    _LOGGER.debug(f"Processing {len(COIL_SENSORS)} coil switches")
    for coil in COIL_SENSORS:
        entities.append(
            DaikinCoilSwitch(
                coordinator=coordinator,
                entry=entry,
                name=coil["name"],
                address=coil["address"],
                unique_id=coil.get("unique_id"),
                translation_key=coil.get("translation_key"),
            )
        )

    async_add_entities(entities)


class DaikinCoilSwitch(CoordinatorEntity, SwitchEntity):
    """A Switch for Coil Register."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, address, unique_id=None, translation_key=None):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._attr_unique_id = unique_id or f"{DOMAIN}_coil_{address}"
        self._attr_device_info = COIL_DEVICE_INFO
        self._attr_icon = "mdi:power"
        self._attr_translation_key = translation_key

    @property
    def is_on(self):
        """Gibt True zurück, wenn der Wert 1 ist."""
        data = self.coordinator.data.get(self._attr_unique_id)
        if data is None:
            return False
        val = data.get("value")
        return val == 1

    async def async_turn_on(self, **kwargs):
        """Schaltet das Coil ein."""
        try:
            result = await self.coordinator.client.write_coil(self._address, True)
            if result.isError():
                _LOGGER.error(f"Failed to turn on coil {self._address}: {result}")
            else:
                _LOGGER.debug(f"Successfully turned on coil {self._address}")
                await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error turning on coil {self._address}: {e}")

    async def async_turn_off(self, **kwargs):
        """Schaltet das Coil aus."""
        try:
            result = await self.coordinator.client.write_coil(self._address, False)
            if result.isError():
                _LOGGER.error(f"Failed to turn off coil {self._address}: {result}")
            else:
                _LOGGER.debug(f"Successfully turned off coil {self._address}")
                await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error turning off coil {self._address}: {e}")
