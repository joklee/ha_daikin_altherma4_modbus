import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..common import (
    get_register_config,
    get_register_scale,
    get_register_value,
    is_entity_available,
    safe_write_register,
)
from ..core.const import DOMAIN
from ..core.register_constants import HOLDING_DEVICE_INFO, HOLDING_REGISTERS
from ..core.register_types import NumberRegister

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0  # Managed by DataUpdateCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator

    if coordinator is None:
        _LOGGER.error("Coordinator not found in runtime data")
        return

    entities = []

    holding_numbers = [
        reg for reg in HOLDING_REGISTERS if isinstance(reg, NumberRegister)
    ]
    for item in holding_numbers:
        address = item.address
        min_v = item.min_value
        max_v = item.max_value
        step = item.step
        unit = item.unit or ""
        data_type = item.data_type
        register_name = item.register_name
        enum_map = item.enum_map
        entity_category = item.entity_category
        translation_key = item.translation_key

        entities.append(
            DaikinNumber(
                coordinator,
                entry,
                address,
                min_v,
                max_v,
                step,
                unit,
                data_type,
                register_name,
                enum_map,
                entity_category,
                translation_key=translation_key,
            )
        )

    async_add_entities(entities)


class DaikinNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        address,
        min_v,
        max_v,
        step,
        unit,
        data_type=None,
        register_name=None,
        enum_map=None,
        entity_category=None,
        translation_key=None,
    ):
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
        self._data_type = data_type
        # Scale only from register_types (data_type.scaling)
        self._scale = getattr(data_type, "scaling", 1) if data_type else 1
        self._coordinator: Any = coordinator  # For writing operations - coordinator has data_manager attribute

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return is_entity_available(self.coordinator.data, self._register_name)

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._register_name)
        if data is None:
            return None
        val = get_register_value(data)
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
        data_scale = get_register_scale(data)

        if data_scale is not None:
            # Value is already scaled by data_manager
            scaled_value = val
        else:
            # Value is not scaled yet, apply scaling
            scaled_value = val * self._scale

        return scaled_value

    @property
    def mode(self):
        """Gibt den Modus für enum_map zurück."""
        if self._enum_map:
            return "slider"  # Force slider mode for enum
        return "slider"

    async def async_set_native_value(self, value):
        # Use pre-computed scale from __init__
        scale = self._scale
        raw = int(value / scale)

        # Get register configuration for range clamping
        register_config = get_register_config(self._register_name)

        # Enhanced debug logging
        _LOGGER.debug(
            f"DEBUG: {self._register_name} conversion - input: {value}, scale: {scale}, "
            f"raw_value: {raw}, data_type: {register_config.data_type.name if register_config and register_config.data_type else 'unknown'}"
        )

        # Apply range clamping based on register configuration
        if (
            register_config
            and hasattr(register_config, "min_value")
            and hasattr(register_config, "max_value")
        ):
            # Use scale from register_config.data_type for clamping
            config_scale = 1
            if register_config.data_type:
                config_scale = getattr(register_config.data_type, "scaling", 1)
            # Clamp to device-specific range
            min_raw = (
                int(register_config.min_value / config_scale)
                if config_scale != 0
                else register_config.min_value
            )
            max_raw = (
                int(register_config.max_value / config_scale)
                if config_scale != 0
                else register_config.max_value
            )
            raw = max(min_raw, min(max_raw, raw))
            _LOGGER.debug(
                f"DEBUG: {self._register_name} clamped to device range {register_config.min_value}-{register_config.max_value}: {raw}"
            )
        else:
            # Clamp to 16-bit range (signed conversion handled by RegisterRepository)
            raw = max(-32768, min(65535, raw))
            _LOGGER.debug(
                f"DEBUG: {self._register_name} clamped to 16-bit range: {raw}"
            )

        _LOGGER.debug(f"DEBUG: {self._register_name} final raw value: {raw}")

        await safe_write_register(
            self._coordinator.data_manager.write_holding_register,
            self._register_name,
            raw,
            operation_name="set value for",
            register_type="number",
            coordinator=self._coordinator,
        )
