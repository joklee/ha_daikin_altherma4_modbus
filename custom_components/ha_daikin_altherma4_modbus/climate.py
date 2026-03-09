"""Climate Entity and Platform for Daikin Altherma 4 Modbus integration."""

import logging
from typing import Any
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CALCULATED_DEVICE_INFO,
    HOLDING_REGISTERS,
    INPUT_REGISTERS,
    REGISTER_OPERATION_MODE,
    HVAC_COOL,
    REGISTER_OFFSET_COOLING,
    REGISTER_OFFSET_HEATING,
    REGISTER_CURRENT_TEMP,
    DHW_OFF,
    DHW_ON,
    REGISTER_DHW_SETPOINT,
    REGISTER_DWH_RUNNING,
    REGISTER_DWH_HVAC_MODE,
    REGISTER_DHW_BOOSTER_SETPOINT,
    REGISTER_DWH_BOOSTER_TEMP,
    REGISTER_DWH_BOOSTER_RUNNING,
    REGISTER_DWH_BOOSTER_HVAC_MODE,
    REGISTER_QUIET_MODE,
    FAN_MANUAL,
    HVAC_HEAT,
    HVAC_OFF,
    REGISTER_COMPRESSOR,
    FAN_AUTO,
    FAN_OFF,
    REGISTER_DWH_TEMP,
)

_LOGGER = logging.getLogger(__name__)


def get_register_scale(unique_id, register_list):
    """Get scale factor for a register by unique_id from const.py."""
    # Try to get scale directly from coordinator data first
    if hasattr(register_list, "coordinator") and register_list.coordinator:
        # Create address_name without DOMAIN prefix for coordinator.data access
        if unique_id.startswith(f"{DOMAIN}_"):
            address_name = unique_id[len(f"{DOMAIN}_") :]
        else:
            address_name = unique_id
        data = register_list.coordinator.data.get(address_name, {})
        if "scale" in data:
            return data["scale"]

    # Fallback to original loop method
    for register in register_list:
        register_unique_id = register.get("unique_id")
        if register_unique_id == unique_id:
            return register.get("scale", 1)
    return 1  # Default scale if not found


class DaikinThermostatClimate(CoordinatorEntity, ClimateEntity):
    """Climate Entity for Daikin Altherma 4 Thermostat Control."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        # Type hint to indicate coordinator has data_manager attribute
        self.coordinator: Any = coordinator  # Coordinator with data_manager attribute
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_thermostat_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        )
        # Register holding_3 supports Auto/Heating/Cooling, but no dedicated Off state.
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
        self._attr_device_info = CALCULATED_DEVICE_INFO
        self._attr_translation_key = "daikin_thermostat_climate"

    def _get_register_data(self, register_name):
        """Get register data without DOMAIN prefix."""
        # Create address_name without DOMAIN prefix for coordinator.data access
        if register_name.startswith(f"{DOMAIN}_"):
            address_name = register_name[len(f"{DOMAIN}_") :]
        else:
            address_name = register_name
        return self.coordinator.data.get(address_name, {})

    def _get_operation_mode(self):
        """Get the current operation mode value."""
        op_mode_data = self._get_register_data(f"{DOMAIN}_{REGISTER_OPERATION_MODE}")
        return op_mode_data.get("value", 0)

    def _get_offset_register_config(self):
        """Get the appropriate offset register config based on operation mode."""
        op_mode_raw = self._get_operation_mode()

        # Use cooling offset when operation mode is COOL (2), otherwise heating offset
        if op_mode_raw == HVAC_COOL:
            return self._get_register_data(f"{DOMAIN}_{REGISTER_OFFSET_COOLING}")
        else:
            return self._get_register_data(f"{DOMAIN}_{REGISTER_OFFSET_HEATING}")

    @property
    def current_temperature(self):
        """Return the current temperature."""
        temp_data = self._get_register_data(f"{DOMAIN}_{REGISTER_CURRENT_TEMP}")
        temp_raw = temp_data.get("value", 0)

        # Check if value is already scaled by checking if scale is stored in data
        data_scale = temp_data.get("scale")

        if data_scale is not None:
            # Value is already scaled by data_manager
            temp = temp_raw
        else:
            # Value is not scaled yet, apply scaling
            temp = temp_raw * temp_data.get("scale", 0.01)  # °C

        return round(temp, 2)

    @property
    def target_temperature(self):
        """Return the current offset value as temperature."""
        offset_data = self._get_offset_data()
        return round(offset_data["offset"], 1)

    def _get_offset_data(self):
        """Get offset data including raw value, scale, and calculated offset."""
        # Get operation mode from input_38
        op_mode_raw = self._get_operation_mode()

        # Use cooling offset when operation mode is COOL (2), otherwise heating offset
        if op_mode_raw == HVAC_COOL:
            offset_data = self._get_register_data(f"{DOMAIN}_{REGISTER_OFFSET_COOLING}")
        else:
            offset_data = self._get_register_data(f"{DOMAIN}_{REGISTER_OFFSET_HEATING}")
        offset_raw = offset_data.get("value", 0)

        # Handle signed 16-bit integers
        if offset_raw > 32767:
            offset_raw = offset_raw - 65536

        # Check if value is already scaled by checking if scale is stored in data
        data_scale = offset_data.get("scale")

        # Get scale from centralized config (always needed for return value)
        config = self._get_offset_register_config()

        if data_scale is not None:
            # Value is already scaled by data_manager
            offset = offset_raw
            scale = data_scale
        else:
            # Value is not scaled yet, apply scaling
            scale = config.get("scale", 1)
            offset = offset_raw * scale  # °C

        return {
            "op_mode_raw": op_mode_raw,
            "offset_raw": offset_raw,
            "offset": offset,
            "scale": scale,
            "config": config,
        }

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature from const.py."""
        config = self._get_offset_register_config()
        return float(config.get("step", 1))

    @property
    def min_temp(self):
        """Return the minimum offset value from const.py."""
        config = self._get_offset_register_config()
        return float(config.get("min_value", -5))

    @property
    def max_temp(self):
        """Return the maximum offset value from const.py."""
        config = self._get_offset_register_config()
        return float(config.get("max_value", 5))

    @property
    def fan_mode(self):
        """Return the current fan mode (quiet mode)."""
        quiet_data = self._get_register_data(f"{DOMAIN}_{REGISTER_QUIET_MODE}")
        quiet_raw = quiet_data.get("value", 0)

        # Keep read mapping aligned with const.SELECT_REGISTERS enum_map for holding_9.
        quiet_modes = {0: FAN_OFF, 1: FAN_AUTO, 2: FAN_MANUAL}
        return quiet_modes.get(quiet_raw, FAN_OFF)

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return [FAN_OFF, FAN_AUTO, FAN_MANUAL]

    @property
    def hvac_mode(self):
        """Return current operation mode."""
        op_mode_raw = self._get_operation_mode()

        mode_map = {
            HVAC_OFF: HVACMode.AUTO,
            HVAC_HEAT: HVACMode.HEAT,
            HVAC_COOL: HVACMode.COOL,
        }
        return mode_map.get(op_mode_raw, HVACMode.AUTO)

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        comp_data = self._get_register_data(f"{DOMAIN}_{REGISTER_COMPRESSOR}")
        comp_raw = comp_data.get("value", 0)

        if comp_raw:
            return (
                HVACAction.HEATING
                if self.hvac_mode == HVACMode.HEAT
                else HVACAction.COOLING
            )
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs):
        """Set new offset temperature directly."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        # Get limits from centralized config
        config = self._get_offset_register_config()
        min_temp = float(config.get("min_value", -5))
        max_temp = float(config.get("max_value", 5))
        offset = max(min_temp, min(max_temp, round(temperature, 0)))

        # Konvertiere zu Rohwert für Holding Register
        offset_raw = int(offset)

        # Handle signed 16-bit integers
        if offset_raw < 0:
            offset_raw = 65536 + offset_raw

        # Get operation mode from input_38 before try block
        offset_data = self._get_offset_data()
        op_mode_raw = offset_data["op_mode_raw"]

        try:
            result = None
            if op_mode_raw == HVAC_COOL:
                result = await self.coordinator.data_manager.write_holding_register(
                    REGISTER_OFFSET_COOLING, offset_raw
                )
            else:
                result = await self.coordinator.data_manager.write_holding_register(
                    REGISTER_OFFSET_HEATING, offset_raw
                )
            if result is None:
                raise HomeAssistantError("Failed to set thermostat offset")
            _LOGGER.debug(f"Set thermostat offset to {offset}°C (raw: {offset_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set thermostat offset: {e}")
            raise HomeAssistantError("Failed to set thermostat offset") from e

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        # Keep semantics explicit: this entity has no native OFF in holding_3.
        # For service compatibility, OFF is coerced to AUTO.
        mode_map = {
            HVACMode.AUTO: 0,
            HVACMode.HEAT: HVAC_HEAT,
            HVACMode.COOL: HVAC_COOL,
            HVACMode.OFF: 0,
        }
        if hvac_mode == HVACMode.OFF:
            _LOGGER.debug(
                "HVAC OFF requested but not supported by holding_3; using AUTO"
            )
        mode_raw = mode_map.get(hvac_mode, 0)

        try:
            result = await self.coordinator.data_manager.write_holding_register(
                REGISTER_OPERATION_MODE, mode_raw
            )
            if result is None:
                raise HomeAssistantError("Failed to set HVAC mode")
            _LOGGER.debug(f"Set HVAC mode to {hvac_mode} (raw: {mode_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set HVAC mode: {e}")
            raise HomeAssistantError("Failed to set HVAC mode") from e

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode (quiet mode)."""
        # Keep write mapping aligned with const.SELECT_REGISTERS enum_map for holding_9.
        fan_map = {FAN_OFF: 0, FAN_AUTO: 1, FAN_MANUAL: 2}
        mode_raw = fan_map.get(fan_mode, 0)

        try:
            result = await self.coordinator.data_manager.write_holding_register(
                REGISTER_QUIET_MODE, mode_raw
            )
            if result is None:
                raise HomeAssistantError("Failed to set fan mode")
            _LOGGER.debug(f"Set fan mode to {fan_mode} (raw: {mode_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set fan mode: {e}")
            raise HomeAssistantError("Failed to set fan mode") from e

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        quiet_data = self._get_register_data(f"{DOMAIN}_{REGISTER_QUIET_MODE}")
        quiet_raw = quiet_data.get("value", 0)
        quiet_map = {0: "Off", 1: "On (Automatic)", 2: "On (Manual)"}
        quiet_mode = quiet_map.get(quiet_raw, "Unknown")

        # Get offset data using helper method
        offset_data_info = self._get_offset_data()
        offset = offset_data_info["offset"]
        op_mode_raw = offset_data_info["op_mode_raw"]
        config = offset_data_info["config"]

        # Berechnete Solltemperatur für Anzeige
        current_temp = self.current_temperature
        calculated_setpoint = current_temp + offset

        return {
            "quiet_mode": quiet_mode,
            "offset": round(offset, 2),
            "calculated_setpoint": round(calculated_setpoint, 2),
            "current_temperature": current_temp,
            "register_config": {
                "address": REGISTER_OFFSET_HEATING
                if op_mode_raw != HVAC_COOL
                else REGISTER_OFFSET_COOLING,
                "min_value": config.get("min_value"),
                "max_value": config.get("max_value"),
                "step": config.get("step"),
                "scale": offset_data_info["scale"],
            },
        }

    async def async_turn_on(self):
        """Turn thermostat control on (mapped to AUTO mode)."""
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self):
        """Compatibility path for turn_off; this thermostat has no native OFF."""
        await self.async_set_hvac_mode(HVACMode.AUTO)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup climate entities."""
    coordinators = hass.data["ha_daikin_altherma4_modbus"][entry.entry_id]
    coordinator = coordinators["coordinator"]

    entities = [
        DaikinThermostatClimate(coordinator, entry),
        DaikinDHWThermostat(coordinator, entry, dhw_type="manual"),
        DaikinDHWThermostat(coordinator, entry, dhw_type="booster"),
    ]

    async_add_entities(entities)
    _LOGGER.debug("Setup Daikin Thermostat Climate entities")


class DaikinDHWThermostat(CoordinatorEntity, ClimateEntity):
    """Climate Entity for DHW Heat-up (Manual or Booster)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, dhw_type="manual"):
        super().__init__(coordinator)
        # Type hint to indicate coordinator has data_manager attribute
        self.coordinator: Any = coordinator  # Coordinator with data_manager attribute
        self._entry = entry
        self._dhw_type = dhw_type

        # Set registers based on DHW type
        if dhw_type == "booster":
            self._hvac_mode_register = REGISTER_DWH_BOOSTER_HVAC_MODE
            self._running_register = REGISTER_DWH_BOOSTER_RUNNING
            self._temp_register = REGISTER_DWH_BOOSTER_TEMP
            self._setpoint_register = REGISTER_DHW_BOOSTER_SETPOINT
            self._unique_id_suffix = "dhw_booster_thermostat"
            self._icon = "mdi:water-boiler-alert"
            self._translation_key = "daikin_dhw_booster_thermostat"
            self._write_register_func = (
                self.coordinator.data_manager.write_holding_register
            )
        else:  # manual
            self._hvac_mode_register = REGISTER_DWH_HVAC_MODE
            self._running_register = REGISTER_DWH_RUNNING
            self._temp_register = REGISTER_DWH_TEMP
            self._setpoint_register = REGISTER_DHW_SETPOINT
            self._unique_id_suffix = "dhw_manual_thermostat"
            self._icon = "mdi:water-boiler"
            self._translation_key = "daikin_dhw_manual_thermostat"
            self._write_register_func = (
                self.coordinator.data_manager.write_coil_register
            )

        self._attr_unique_id = f"{DOMAIN}_{self._unique_id_suffix}"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_min_temp = 30
        self._attr_max_temp = 85
        self._attr_target_temperature_step = 0.5
        self._attr_icon = self._icon
        self._attr_device_info = CALCULATED_DEVICE_INFO
        self._attr_translation_key = self._translation_key

    def _get_register_data(self, register_name):
        """Get register data without DOMAIN prefix."""
        # Create address_name without DOMAIN prefix for coordinator.data access
        if register_name.startswith(f"{DOMAIN}_"):
            address_name = register_name[len(f"{DOMAIN}_") :]
        else:
            address_name = register_name
        return self.coordinator.data.get(address_name, {})

    def _get_scaled_register_value(self, register_name, register_type):
        """Get scaled value from a register."""
        data = self._get_register_data(f"{DOMAIN}_{register_name}")
        if data is None:
            return None

        scale_factor = get_register_scale(f"{DOMAIN}_{register_name}", register_type)
        raw_value = data.get("value")
        return raw_value * scale_factor if raw_value is not None else None

    @property
    def hvac_mode(self):
        data = self._get_register_data(f"{DOMAIN}_{self._hvac_mode_register}")
        if data is None:
            return HVACMode.OFF

        val = data.get("value")
        return HVACMode.HEAT if val == DHW_ON else HVACMode.OFF

    @property
    def hvac_action(self):
        """Return current HVAC action."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        # Check if DHW is actually running
        data = self._get_register_data(f"{DOMAIN}_{self._running_register}")
        if data is None:
            return HVACAction.IDLE

        val = data.get("value")
        return HVACAction.HEATING if val == DHW_ON else HVACAction.IDLE

    @property
    def current_temperature(self):
        """Return current temperature."""
        # Use DHW temperature as current temperature
        return self._get_scaled_register_value(self._temp_register, INPUT_REGISTERS)

    @property
    def target_temperature(self):
        """Return target temperature."""
        return self._get_scaled_register_value(
            self._setpoint_register, HOLDING_REGISTERS
        )

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            try:
                result = await self._write_register_func(
                    self._hvac_mode_register, DHW_ON
                )
                if result is None:
                    _LOGGER.error(f"Failed to turn on {self._dhw_type} DHW heat-up")
                else:
                    _LOGGER.debug(
                        f"Successfully turned on {self._dhw_type} DHW heat-up"
                    )
            except Exception as e:
                _LOGGER.error(f"Error turning on {self._dhw_type} DHW heat-up: {e}")
        elif hvac_mode == HVACMode.OFF:
            try:
                result = await self._write_register_func(
                    self._hvac_mode_register, DHW_OFF
                )
                if result is None:
                    _LOGGER.error(f"Failed to turn off {self._dhw_type} DHW heat-up")
                else:
                    _LOGGER.debug(
                        f"Successfully turned off {self._dhw_type} DHW heat-up"
                    )
            except Exception as e:
                _LOGGER.error(f"Error turning off {self._dhw_type} DHW heat-up: {e}")

    async def async_set_temperature(self, **kwargs):
        """Set target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        # Get scale factor from const.py for DHW setpoint
        scale_factor = get_register_scale(
            f"{DOMAIN}_{self._setpoint_register}", HOLDING_REGISTERS
        )

        # Convert temperature to raw register value
        raw_value = (
            int(temperature / scale_factor) if scale_factor != 0 else int(temperature)
        )
        try:
            result = await self.coordinator.data_manager.write_holding_register(
                self._setpoint_register, raw_value
            )
            if result is None:
                _LOGGER.error(f"Failed to set {self._dhw_type} DHW heat-up temperature")
            else:
                _LOGGER.debug(
                    f"Successfully set {self._dhw_type} DHW heat-up temperature to {temperature}°C (raw: {raw_value})"
                )
        except Exception as e:
            _LOGGER.error(
                f"Error setting {self._dhw_type} DHW heat-up temperature: {e}"
            )

    async def async_turn_on(self):
        """Turn on DHW heat-up."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn off DHW heat-up."""
        await self.async_set_hvac_mode(HVACMode.OFF)
