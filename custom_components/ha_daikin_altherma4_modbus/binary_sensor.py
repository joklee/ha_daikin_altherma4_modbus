import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory
from .const import DOMAIN, BINARY_SENSORS, INPUT_DEVICE_INFO, DISCRETE_INPUT_SENSORS, DISCRETE_INPUT_DEVICE_INFO

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup aller Binary Sensors über Config Entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for binary in BINARY_SENSORS:
        entities.append(
            DaikinBinarySensor(
                coordinator=coordinator,
                entry=entry,
                name=binary["name"],
                address=binary["address"],
                device_class=binary["device_class"],
                entity_category=binary.get("entity_category"),
                unique_id=binary.get("unique_id"),
                translation_key=binary.get("translation_key"),
            )
        )

    # Discrete Input Sensors
    _LOGGER.debug(f"Processing {len(DISCRETE_INPUT_SENSORS)} discrete input sensors")
    for discrete in DISCRETE_INPUT_SENSORS:
        entities.append(
            DaikinDiscreteInputSensor(
                coordinator=coordinator,
                entry=entry,
                name=discrete["name"],
                address=discrete["address"],
                device_class=discrete["device_class"],
                entity_category=discrete.get("entity_category"),
                unique_id=discrete.get("unique_id"),
                translation_key=discrete.get("translation_key"),
            )
        )

    async_add_entities(entities)


class DaikinBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Ein Binary Sensor für Modbus-Register."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, address, device_class, entity_category=None, unique_id=None, translation_key=None):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._attr_unique_id = unique_id or f"{DOMAIN}_{address}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_device_info = INPUT_DEVICE_INFO
        self._attr_translation_key = translation_key

    @property
    def is_on(self):
        """Gibt True zurück, wenn der Wert 1 ist."""
        data = self.coordinator.data.get(self._attr_unique_id)
        if data is None:
            return False
        val = data.get("value")
        return val == 1


class DaikinDiscreteInputSensor(CoordinatorEntity, BinarySensorEntity):
    """A Binary Sensor for Discrete Input Register."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, address, device_class, entity_category=None, unique_id=None, translation_key=None):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._attr_unique_id = unique_id or f"{DOMAIN}_discrete_{address}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_device_info = DISCRETE_INPUT_DEVICE_INFO
        self._attr_translation_key = translation_key

    @property
    def is_on(self):
        """Gibt True zurück, wenn der Wert 1 ist."""
        data = self.coordinator.data.get(self._attr_unique_id)
        if data is None:
            return False
        val = data.get("value")
        return val == 1