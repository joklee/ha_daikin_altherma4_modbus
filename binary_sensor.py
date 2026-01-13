import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory
from .const import DOMAIN, BINARY_SENSORS, UNIQUE_ID_PREFIX, DEVICE_INFO

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
            )
        )

    async_add_entities(entities)


class DaikinBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Ein Binary Sensor für Modbus-Register."""

    def __init__(self, coordinator, entry, name, address, device_class, entity_category=None):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"{UNIQUE_ID_PREFIX}binary_{address}"
        self._attr_device_class = device_class
        if entity_category == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DEVICE_INFO

    @property
    def is_on(self):
        """Gibt True zurück, wenn der Wert 1 ist."""
        val = self.coordinator.data.get(self._address)
        return val == 1