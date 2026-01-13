from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, HOLDING_REGISTERS

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for name, address, min_v, max_v, step, unit, scale in HOLDING_REGISTERS:
        entities.append(
            DaikinNumber(coordinator, entry, name, address, min_v, max_v, step, unit, scale)
        )

    async_add_entities(entities)


class DaikinNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, entry, name, address, min_v, max_v, step, unit, scale):
        super().__init__(coordinator)

        self._entry = entry
        self._address = address
        self._scale = scale

        self._attr_name = f"ModbusAltherma4 - {name}"
        self._attr_unique_id = f"{entry.entry_id}_holding_{address}"
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    async def async_set_native_value(self, value):
        raw = int(value / self._scale)
        await self.coordinator.client.write_register(self._address, raw)
        await self.coordinator.async_request_refresh()
