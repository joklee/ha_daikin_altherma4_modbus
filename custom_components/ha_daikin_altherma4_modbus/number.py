from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, HOLDING_REGISTERS, HOLDING_DEVICE_INFO
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinators.get("coordinator")
    
    if coordinator is None:
        _LOGGER.error("Coordinator not found in hass data")
        return
    
    entities = []

    for item in HOLDING_REGISTERS:
        address = item["address"]
        min_v = item.get("min_value", 0)
        max_v = item.get("max_value", 100)
        step = item.get("step", 1)
        unit = item.get("unit", "")
        scale = item.get("scale", 1)
        register_name = item.get("register_name")
        enum_map = item.get("enum_map")
        entity_category = item.get("entity_category")
        translation_key = item.get("translation_key")
        
        entities.append(
            DaikinNumber(coordinator, entry, address, min_v, max_v, step, unit, scale, register_name, enum_map, entity_category, translation_key=translation_key)
        )

    async_add_entities(entities)


class DaikinNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, entry, address, min_v, max_v, step, unit, scale, register_name, enum_map=None, entity_category=None, translation_key=None):
        super().__init__(coordinator)

        self._entry = entry
        self._address = address
        self._min_value = min_v
        self._max_value = max_v
        self._step = step
        self._register_name = register_name
        self._attr_unique_id = f"{DOMAIN}_{register_name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_entity_category = entity_category
        self._attr_device_info = HOLDING_DEVICE_INFO
        self._attr_translation_key = translation_key
        self._enum_map = enum_map
        self._scale = scale
        self._coordinator: Any = coordinator  # For writing operations - coordinator has data_manager attribute

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        data = self.coordinator.data.get(self._register_name)
        if data is None:
            return False
        
        val = data.get("value")
        if val is None:
            return False
            
        # Convert to integer if it's a string
        try:
            val = int(val)
        except (ValueError, TypeError):
            return False
            
        # Sensor is unavailable if value is 32765 or 32766
        if val == 32765 or val == 32766:
            return False
            
        return True

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._register_name)
        if data is None:
            return None
        val = data.get("value")
        if val is None:
            return None
        
        # Convert to integer if it's a string
        try:
            val = int(val)
        except (ValueError, TypeError):
            return None
            
        # Return None for unavailable value (32765 or 32766)
        if val == 32765 or val == 32766:
            return None
        
        # Wenn enum_map vorhanden, den enum-Wert zurückgeben
        if self._enum_map and val in self._enum_map:
            return val  # Rohwert für enum
        
        # Check if value is already scaled by checking if scale is stored in data
        data_scale = data.get("scale")
        
        if data_scale is not None:
            # Value is already scaled by data_manager
            scaled_value = val
        else:
            # Value is not scaled yet, apply scaling
            # Handle signed 16-bit integers
            if val > 32767:  # If value is negative (2's complement)
                val = val - 65536
            scaled_value = val * self._scale
            
        return scaled_value

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
            
        await self._coordinator.data_manager.write_holding_register(self._register_name, raw)
