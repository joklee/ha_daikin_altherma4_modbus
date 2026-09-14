import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..common import get_coordinator_from_entry, get_register_value, is_entity_available
from ..core.const import DOMAIN
from ..core.register_constants import (
    CALCULATED_DEVICE_INFO,
    CONNECTION_SENSORS,
    DISCRETE_INPUT_DEVICE_INFO,
    DISCRETE_REGISTERS,
    INPUT_DEVICE_INFO,
    INPUT_REGISTERS,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0  # Managed by DataUpdateCoordinator


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
    _LOGGER.debug(f"Processing {len(DISCRETE_REGISTERS)} discrete input sensors")
    for discrete in DISCRETE_REGISTERS:
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

    # Connection diagnostic sensor on the "Enhanced" device: whether any
    # coordinator currently holds a connected transport client.
    for conn in CONNECTION_SENSORS:
        if conn.calc_type != "connection_active":
            continue
        entities.append(
            ConnectionActiveSensor(
                coordinator=coordinator,
                entry=entry,
                unique_id=conn.register_name,
                device_class=conn.device_class or BinarySensorDeviceClass.CONNECTIVITY,
                entity_category=conn.entity_category or EntityCategory.DIAGNOSTIC,
                device_info=CALCULATED_DEVICE_INFO,
                translation_key=conn.translation_key,
            )
        )

    async_add_entities(entities)


class DaikinBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Ein Binary Sensor für Modbus-Register."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

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
    _attr_log_when_unavailable = False

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


class ConnectionActiveSensor(CoordinatorEntity, BinarySensorEntity):
    """Diagnostic sensor: is the shared Modbus transport connected?

    Lives on the "Enhanced" device. The value is served live from the
    CoordinatorManager (any coordinator holding a connected client), so it
    keeps reporting during polling outages instead of going unavailable.
    """

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        device_class=None,
        entity_category=None,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key

    def _manager(self):
        """Return the CoordinatorManager behind the unified coordinator."""
        return getattr(self.coordinator, "manager", None)

    @property
    def available(self) -> bool:
        """Available whenever the manager is reachable."""
        return self._manager() is not None

    @property
    def is_on(self):
        """True while any coordinator holds a connected transport client."""
        manager = self._manager()
        if manager is None:
            return None
        return bool(manager.connection_active)
