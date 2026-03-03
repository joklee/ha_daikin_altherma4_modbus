import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, INPUT_REGISTERS, INPUT_DEVICE_INFO, DISCRETE_INPUT_SENSORS, DISCRETE_INPUT_DEVICE_INFO

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup aller Binary Sensors über Config Entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinators.get("coordinator")
    
    if coordinator is None:
        _LOGGER.error("Coordinator not found in hass data")
        return
    
    entities = []

    # Process binary sensors from INPUT_REGISTERS with device_class
    for item in INPUT_REGISTERS:
        device_class = item.get("device_class")
        if device_class in ["running", "problem"]:
            entities.append(
                DaikinBinarySensor(
                    coordinator=coordinator,
                    entry=entry,
                    address=item["address"],
                    device_class=device_class,
                    register_name=item.get("register_name"),
                    entity_category=item.get("entity_category"),
                    unique_id=item.get("register_name"),
                    translation_key=item.get("translation_key"),
                )
            )

    # Discrete Input Sensors
    _LOGGER.debug(f"Processing {len(DISCRETE_INPUT_SENSORS)} discrete input sensors")
    for discrete in DISCRETE_INPUT_SENSORS:
        entities.append(
            DaikinDiscreteInputSensor(
                coordinator=coordinator,
                entry=entry,
                address=discrete["address"],
                device_class=discrete["device_class"],
                entity_category=discrete.get("entity_category"),
                register_name=discrete.get("register_name"),
                unique_id=discrete.get("register_name"),
                translation_key=discrete.get("translation_key"),
            )
        )

    async_add_entities(entities)


class DaikinBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Ein Binary Sensor für Modbus-Register."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, address, device_class, register_name,entity_category=None, unique_id=None, translation_key=None):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._attr_register_name = register_name
        self._attr_unique_id = unique_id or f"{DOMAIN}_{register_name}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_device_info = INPUT_DEVICE_INFO
        self._attr_translation_key = translation_key

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        data = self.coordinator.data.get(self._attr_register_name)
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
    def is_on(self):
        data = self.coordinator.data.get(self._attr_register_name)
        if data is None:
            return False
        val = data.get("value")
        return val == 1


class DaikinDiscreteInputSensor(CoordinatorEntity, BinarySensorEntity):
    """A Binary Sensor for Discrete Input Register."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, address, device_class, register_name, entity_category=None, unique_id=None, translation_key=None):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._attr_register_name = register_name
        self._attr_unique_id = unique_id or f"{DOMAIN}_{register_name}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_device_info = DISCRETE_INPUT_DEVICE_INFO
        self._attr_translation_key = translation_key

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        data = self.coordinator.data.get(self._attr_register_name)
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
    def is_on(self):
        """Gibt True zurück, wenn der Wert 1 ist."""
        data = self.coordinator.data.get(self._attr_register_name)
        if data is None:
            return False
        val = data.get("value")
        return val == 1