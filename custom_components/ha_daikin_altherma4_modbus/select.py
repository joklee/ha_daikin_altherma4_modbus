"""Select platform for Daikin Altherma 4 Modbus integration."""
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory
from .const import DOMAIN, SELECT_REGISTERS, HOLDING_DEVICE_INFO

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup select entities over Config Entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for item in SELECT_REGISTERS:
        if item.get("enum_map"):  # Nur für Register mit enum_map
            name = item["name"]
            address = item["address"]
            unique_id = item.get("unique_id", f"{DOMAIN}_holding_{address}")
            enum_map = item["enum_map"]
            entity_category = item.get("entity_category")
            
            entities.append(
                DaikinSelect(coordinator, entry, name, address, unique_id, enum_map, entity_category)
            )

    async_add_entities(entities)


class DaikinSelect(CoordinatorEntity, SelectEntity):
    """Select entity for Daikin Altherma 4."""

    def __init__(self, coordinator, entry, name, address, unique_id, enum_map, entity_category=None):
        super().__init__(coordinator)

        self._entry = entry
        self._address = address
        self._enum_map = enum_map

        self._attr_name = name
        self._attr_unique_id = unique_id or f"{DOMAIN}_{address}"
        self._attr_device_info = HOLDING_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_options = list(enum_map.values())

    @property
    def current_option(self):
        """Return current selected option."""
        data = self.coordinator.data.get(self._attr_unique_id)
        _LOGGER.debug(f"Select {self._attr_name} - data: {data}")
        
        if data:
            val = data.get("value")
            _LOGGER.debug(f"Select {self._attr_name} - raw value: {val}")
            
            if val is not None and val in self._enum_map:
                option = self._enum_map[val]
                _LOGGER.debug(f"Select {self._attr_name} - mapped option: {option}")
                return option
            else:
                _LOGGER.warning(f"Select {self._attr_name} - value {val} not in enum_map: {self._enum_map}")
        
        _LOGGER.debug(f"Select {self._attr_name} - no data or value, returning None")
        return None

    async def async_select_option(self, option: str):
        """Change the selected option."""
        # Find the key for the selected option
        for key, value in self._enum_map.items():
            if value == option:
                await self.coordinator.client.write_register(self._address, key)
                await self.coordinator.async_request_refresh()
                break
