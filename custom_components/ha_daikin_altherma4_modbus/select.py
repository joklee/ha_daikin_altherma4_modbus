"""Select platform for Daikin Altherma 4 Modbus integration."""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .common import (
    get_coordinator_from_entry,
    get_register_value,
    is_entity_available,
    safe_write_register,
)
from .const import DOMAIN, HOLDING_DEVICE_INFO, SELECT_REGISTERS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup select entities over Config Entry."""
    coordinator = get_coordinator_from_entry(hass, entry)
    if coordinator is None:
        return

    entities = []

    for item in SELECT_REGISTERS:
        if item.enum_map:  # Nur für Register mit enum_map
            address = item.address
            register_name = item.register_name
            enum_map = item.enum_map
            entity_category = item.entity_category
            translation_key = item.translation_key

            entities.append(
                DaikinSelect(
                    coordinator,
                    entry,
                    address,
                    register_name,
                    enum_map,
                    entity_category,
                    translation_key,
                )
            )

    async_add_entities(entities)


class DaikinSelect(CoordinatorEntity, SelectEntity):
    """Select entity for Daikin Altherma 4."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry,
        address,
        register_name,
        enum_map,
        entity_category=None,
        translation_key=None,
    ):
        super().__init__(coordinator)

        self._entry = entry
        self._address = address
        self._enum_map = enum_map
        self._coordinator: Any = coordinator  # For writing operations - coordinator has data_manager attribute
        self._register_name = register_name

        self._attr_unique_id = f"{DOMAIN}_{register_name}"
        self._attr_device_info = HOLDING_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_options = list(enum_map.values())
        self._attr_translation_key = translation_key

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return is_entity_available(self.coordinator.data, self._register_name)

    @property
    def current_option(self):
        data = self.coordinator.data.get(self._register_name)

        if data:
            val = get_register_value(data)

            # Convert to integer if it's a string
            try:
                val = int(val)
            except (ValueError, TypeError):
                return None

            # Return None for unavailable value (32765 or 32766)
            if val == 32765 or val == 32766:
                return None

            if val is not None and val in self._enum_map:
                option = self._enum_map[val]
                return option

        return None

    async def async_select_option(self, option: str):
        """Change the selected option."""
        # Find the key for the selected option
        for key, value in self._enum_map.items():
            if value == option:
                if hasattr(self._coordinator, "data_manager"):
                    await safe_write_register(
                        self._coordinator.data_manager.write_holding_register,
                        self._register_name,
                        key,
                        operation_name="set option for",
                        register_type="select",
                    )
                else:
                    raise HomeAssistantError(
                        "Coordinator does not have data_manager attribute"
                    )
                return

        raise HomeAssistantError(
            f"Unsupported option '{option}' for {self._register_name}"
        )
