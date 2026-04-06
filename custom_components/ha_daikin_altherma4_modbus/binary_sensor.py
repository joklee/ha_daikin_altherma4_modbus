import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .common import get_coordinator_from_entry, get_register_value, is_entity_available
from .const import (
    DISCRETE_INPUT_DEVICE_INFO,
    DISCRETE_INPUT_SENSORS,
    DOMAIN,
    INPUT_DEVICE_INFO,
    INPUT_REGISTERS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup aller Binary Sensors über Config Entry."""
    coordinator = get_coordinator_from_entry(hass, entry)
    if coordinator is None:
        return

    entities = []

    # Process binary sensors from INPUT_REGISTERS with device_class
    for item in INPUT_REGISTERS:
        device_class = item.device_class
        if device_class in ["running", "problem"]:
            entities.append(
                DaikinBinarySensor(
                    coordinator=coordinator,
                    entry=entry,
                    address=item.address,
                    device_class=device_class,
                    register_name=item.register_name,
                    entity_category=item.entity_category,
                    unique_id=item.register_name,
                    translation_key=item.translation_key,
                )
            )

    # Discrete Input Sensors
    _LOGGER.debug(f"Processing {len(DISCRETE_INPUT_SENSORS)} discrete input sensors")
    for discrete in DISCRETE_INPUT_SENSORS:
        entities.append(
            DaikinDiscreteInputSensor(
                coordinator=coordinator,
                entry=entry,
                address=discrete.address,
                device_class=discrete.device_class,
                entity_category=discrete.entity_category,
                register_name=discrete.register_name,
                unique_id=discrete.register_name,
                translation_key=discrete.translation_key,
            )
        )

    async_add_entities(entities)


class DaikinBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Ein Binary Sensor für Modbus-Register."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry,
        address,
        device_class,
        register_name,
        entity_category=None,
        unique_id=None,
        translation_key=None,
    ):
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
        return is_entity_available(self.coordinator.data, self._attr_register_name)

    @property
    def is_on(self):
        data = self.coordinator.data.get(self._attr_register_name)
        if data is None:
            return False
        val = get_register_value(data)
        return val == 1


class DaikinDiscreteInputSensor(CoordinatorEntity, BinarySensorEntity):
    """A Binary Sensor for Discrete Input Register."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry,
        address,
        device_class,
        register_name,
        entity_category=None,
        unique_id=None,
        translation_key=None,
    ):
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
        return is_entity_available(self.coordinator.data, self._attr_register_name)

    @property
    def is_on(self):
        """Gibt True zurück, wenn der Wert 1 ist."""
        data = self.coordinator.data.get(self._attr_register_name)
        if data is None:
            return False
        val = get_register_value(data)
        return val == 1
