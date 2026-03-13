"""Switch platform for Daikin Altherma 4 Modbus integration."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .common import safe_write_register
from .const import (
    COIL_DEVICE_INFO,
    COIL_SENSORS,
    DOMAIN,
    HOLDING_DEVICE_INFO,
    HOLDING_SWITCHES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup switch entities over Config Entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    if coordinator is None:
        _LOGGER.error("Coordinator not found in runtime data")
        return
    entities = []

    # Coil Switches
    _LOGGER.debug(f"Processing {len(COIL_SENSORS)} coil switches")
    for coil in COIL_SENSORS:
        entities.append(
            DaikinCoilSwitch(
                coordinator=coordinator,
                entry=entry,
                address=coil["address"],
                register_name=coil.get("register_name"),
                translation_key=coil.get("translation_key"),
            )
        )

    # Holding Register Switches
    _LOGGER.debug(f"Processing {len(HOLDING_SWITCHES)} holding switches")
    for holding_switch in HOLDING_SWITCHES:
        _LOGGER.debug(
            f"Creating holding switch: {holding_switch['name']} (address: {holding_switch['address']}, register: {holding_switch.get('register_name')})"
        )
        entities.append(
            DaikinHoldingSwitch(
                coordinator=coordinator,
                entry=entry,
                address=holding_switch["address"],
                register_name=holding_switch.get("register_name"),
                translation_key=holding_switch.get("translation_key"),
                enum_map=holding_switch.get("enum_map"),
            )
        )

    _LOGGER.debug(f"Total entities to add: {len(entities)}")
    async_add_entities(entities)


class DaikinCoilSwitch(CoordinatorEntity, SwitchEntity):
    """A Switch for Coil Register."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = True

    def __init__(
        self, coordinator, entry, address, register_name, translation_key=None
    ):
        super().__init__(coordinator)
        # Type hint to indicate coordinator has data_manager attribute
        self.coordinator: Any = coordinator  # Coordinator with data_manager attribute
        self._entry = entry
        self._address = address
        self._register_name = register_name
        self._attr_unique_id = f"{DOMAIN}_{register_name}"
        self._attr_device_info = COIL_DEVICE_INFO
        self._attr_icon = "mdi:power"
        self._attr_translation_key = translation_key

    @property
    def is_on(self):
        data = self.coordinator.data.get(self._register_name)
        if data is None:
            return False
        val = data.get("value")
        return val == 1

    async def async_turn_on(self, **kwargs):
        """Schaltet das Coil ein."""
        await safe_write_register(
            self.coordinator.data_manager.write_coil_register,
            self._register_name,
            True,
            operation_name="turn on",
            register_type="coil",
        )
        _LOGGER.debug(f"Successfully turned on coil {self._address}")

    async def async_turn_off(self, **kwargs):
        """Schaltet das Coil aus."""
        await safe_write_register(
            self.coordinator.data_manager.write_coil_register,
            self._register_name,
            False,
            operation_name="turn off",
            register_type="coil",
        )
        _LOGGER.debug(f"Successfully turned off coil {self._address}")


class DaikinHoldingSwitch(CoordinatorEntity, SwitchEntity):
    """A Switch for Holding Register."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = True

    def __init__(
        self,
        coordinator,
        entry,
        address,
        register_name,
        translation_key=None,
        enum_map=None,
    ):
        super().__init__(coordinator)
        # Type hint to indicate coordinator has data_manager attribute
        self.coordinator: Any = coordinator  # Coordinator with data_manager attribute
        self._entry = entry
        self._address = address
        self._register_name = register_name
        self._attr_unique_id = f"{DOMAIN}_{register_name}"
        self._attr_device_info = HOLDING_DEVICE_INFO
        self._attr_icon = "mdi:power"
        self._attr_translation_key = translation_key
        self._enum_map = enum_map or {}
        self._on_value = self._resolve_enum_value(default=1, state_name="on")
        self._off_value = self._resolve_enum_value(default=0, state_name="off")

    def _resolve_enum_value(self, default: int, state_name: str) -> int:
        """Resolve enum value for on/off states when available."""
        if not self._enum_map:
            return default

        for key, label in self._enum_map.items():
            if not isinstance(key, int) or not isinstance(label, str):
                continue
            normalized = label.strip().lower()
            if normalized.startswith(state_name):
                return key

        return default

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data.get(self._register_name) is not None

    @property
    def is_on(self):
        data = self.coordinator.data.get(self._register_name)
        _LOGGER.debug(f"Holding switch {self._register_name} data: {data}")
        if data is None:
            _LOGGER.warning(f"No data found for holding switch {self._register_name}")
            return False
        val = data.get("value")
        _LOGGER.debug(f"Holding switch {self._register_name} value: {val}")
        # For enum switches, check if value corresponds to "On" state
        if self._enum_map:
            return val == self._on_value
        return val == 1

    async def async_turn_on(self, **kwargs):
        """Schaltet das Holding Register ein."""
        await safe_write_register(
            self.coordinator.data_manager.write_holding_register,
            self._register_name,
            self._on_value,
            operation_name="turn on",
            register_type="holding register",
        )
        _LOGGER.debug(f"Successfully turned on holding register {self._address}")

    async def async_turn_off(self, **kwargs):
        """Schaltet das Holding Register aus."""
        await safe_write_register(
            self.coordinator.data_manager.write_holding_register,
            self._register_name,
            self._off_value,
            operation_name="turn off",
            register_type="holding register",
        )
        _LOGGER.debug(f"Successfully turned off holding register {self._address}")
