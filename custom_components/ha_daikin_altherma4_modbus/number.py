from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory
from .const import DOMAIN, HOLDING_REGISTERS, DEVICE_INFO
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for item in HOLDING_REGISTERS:
        name = item["name"]
        address = item["address"]
        min_v = item.get("min_value", 0)
        max_v = item.get("max_value", 100)
        step = item.get("step", 1)
        unit = item.get("unit", "")
        scale = item.get("scale", 1)
        unique_id = item.get("unique_id", f"{DOMAIN}_holding_{address}")
        enum_map = item.get("enum_map")
        entity_category = item.get("entity_category")
        
        entities.append(
            DaikinNumber(coordinator, entry, name, address, min_v, max_v, step, unit, scale, unique_id, enum_map, entity_category)
        )

    async_add_entities(entities)


class DaikinNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, entry, name, address, min_v, max_v, step, unit, scale, unique_id=None, enum_map=None, entity_category=None):
        super().__init__(coordinator)

        self._entry = entry
        self._address = address
        self._scale = scale
        self._enum_map = enum_map

        self._attr_name = name
        self._attr_unique_id = unique_id or f"{DOMAIN}_{address}"
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_device_info = DEVICE_INFO

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._attr_unique_id)
        if data is None:
            return None
        val = data.get("value")
        if val is None:
            return None
        
        # Wenn enum_map vorhanden, den enum-Wert zurückgeben
        if self._enum_map and val in self._enum_map:
            return val  # Rohwert für enum
        
        # Handle signed 16-bit integers
        if val > 32767:  # If value is negative (2's complement)
            val = val - 65536
            
        return val * self._scale

    @property
    def mode(self):
        """Gibt den Modus für enum_map zurück."""
        if self._enum_map:
            return "slider"  # Force slider mode for enum
        return "slider"

    async def async_set_native_value(self, value):
        raw = int(value / self._scale)
        
        # Handle signed 16-bit integers for negative values
        if raw < 0:
            raw = 65536 + raw  # Convert negative to 2's complement
            
        await self.coordinator.client.write_register(self._address, raw)
        await self.coordinator.async_request_refresh()
