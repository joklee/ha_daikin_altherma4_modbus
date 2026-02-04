"""Climate Entity and Platform for Daikin Altherma 4 Modbus integration."""
import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, HOLDING_DEVICE_INFO, HOLDING_REGISTERS, INPUT_REGISTERS

_LOGGER = logging.getLogger(__name__)


def get_register_scale(address, register_list):
    """Get scale factor for a register address from const.py."""
    for register in register_list:
        if register.get("address") == address:
            return register.get("scale", 1)
    return 1  # Default scale if not found

# Register constants for Daikin Altherma 4
REGISTER_CURRENT_TEMP = 41  # Leaving water temperature BUH
REGISTER_OFFSET = 54        # Weather-dependent mode Main LWT Heating setpoint offset
REGISTER_OPERATION_MODE = 3  # Operation mode
REGISTER_QUIET_MODE = 9     # Quiet mode operation
REGISTER_COMPRESSOR = 31    # Compressor status

# Fan mode constants (quiet mode)
FAN_OFF = "OFF"
FAN_AUTO = "On (Automatic)"
FAN_MANUAL = "On (Manual)"

class DaikinThermostatClimate(CoordinatorEntity, ClimateEntity):
    """Climate Entity for Daikin Altherma 4 Thermostat Control."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_thermostat_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        )
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
        self._attr_device_info = HOLDING_DEVICE_INFO
        self._attr_translation_key = "daikin_thermostat_climate"

    def _get_offset_register_config(self):
        """Get configuration for holding register 53 (offset)."""
        for register in HOLDING_REGISTERS:
            if register.get("address") == REGISTER_OFFSET:
                return register
        
        # Error if register not found
        _LOGGER.error(f"Holding register {REGISTER_OFFSET} (offset) not found in HOLDING_REGISTERS!")
        raise ValueError(f"Holding register {REGISTER_OFFSET} configuration missing")

    @property
    def current_temperature(self):
        """Return the current temperature."""
        # Istwert aus Input Register 40 (Leaving water temperature BUH)
        temp_data = self.coordinator.data.get(f"{DOMAIN}_input_{REGISTER_CURRENT_TEMP}", {})
        temp_raw = temp_data.get("value", 0)
        temp = temp_raw * temp_data.get("scale", 0.01)  # °C
        return round(temp, 2)

    @property
    def target_temperature(self):
        """Return the current offset value as temperature."""
        # Offset aus Holding Register 53
        offset_data = self.coordinator.data.get(f"{DOMAIN}_holding_{REGISTER_OFFSET}", {})
        offset_raw = offset_data.get("value", 0)
        
        # Handle signed 16-bit integers
        if offset_raw > 32767:
            offset_raw = offset_raw - 65536
        
        # Get scale from centralized config
        config = self._get_offset_register_config()
        scale = config.get("scale", 1)
        offset = offset_raw * scale  # °C
        
        return round(offset, 1)

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
        quiet_data = self.coordinator.data.get(f"{DOMAIN}_holding_{REGISTER_QUIET_MODE}", {})
        quiet_raw = quiet_data.get("value", 0)
        
        fan_map = {0: FAN_OFF, 1: FAN_AUTO, 2: FAN_MANUAL}
        return fan_map.get(quiet_raw, FAN_OFF)

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return [FAN_OFF, FAN_AUTO, FAN_MANUAL]

    @property
    def hvac_mode(self):
        """Return current operation mode."""
        # Operation mode aus Holding Register 2
        op_mode_data = self.coordinator.data.get(f"{DOMAIN}_holding_{REGISTER_OPERATION_MODE}", {})
        op_mode_raw = op_mode_data.get("value", 0)
        
        mode_map = {0: HVACMode.AUTO, 1: HVACMode.HEAT, 2: HVACMode.COOL}
        return mode_map.get(op_mode_raw, HVACMode.AUTO)

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        # Compressor status aus Input Register 30
        comp_data = self.coordinator.data.get(f"{DOMAIN}_input_{REGISTER_COMPRESSOR}", {})
        comp_raw = comp_data.get("value", 0)
        
        if comp_raw:
            return HVACAction.HEATING if self.hvac_mode == HVACMode.HEAT else HVACAction.COOLING
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
        
        # Begrenze den Offset auf die Werte aus Holding Register 53
        offset = max(min_temp, min(max_temp, round(temperature, 0)))
        
        # Konvertiere zu Rohwert für Holding Register
        offset_raw = int(offset)
        
        # Handle signed 16-bit integers
        if offset_raw < 0:
            offset_raw = 65536 + offset_raw
        
        # Schreibe neuen Offset in Holding Register 53
        try:
            await self.coordinator.client.write_register(REGISTER_OFFSET, offset_raw)
            await self.coordinator.async_request_refresh()
            _LOGGER.debug(f"Set thermostat offset to {offset}°C (raw: {offset_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set thermostat offset: {e}")

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        mode_map = {HVACMode.AUTO: 0, HVACMode.HEAT: 1, HVACMode.COOL: 2}
        mode_raw = mode_map.get(hvac_mode, 0)
        
        try:
            await self.coordinator.client.write_register(REGISTER_OPERATION_MODE, mode_raw)
            await self.coordinator.async_request_refresh()
            _LOGGER.debug(f"Set HVAC mode to {hvac_mode} (raw: {mode_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set HVAC mode: {e}")

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode (quiet mode)."""
        fan_map = {FAN_OFF: 0, FAN_AUTO: 1, FAN_MANUAL: 2}
        mode_raw = fan_map.get(fan_mode, 0)
        
        try:
            await self.coordinator.client.write_register(REGISTER_QUIET_MODE, mode_raw)
            await self.coordinator.async_request_refresh()
            _LOGGER.debug(f"Set fan mode to {fan_mode} (raw: {mode_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set fan mode: {e}")

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        # Quiet mode aus Holding Register 8
        quiet_data = self.coordinator.data.get(f"{DOMAIN}_holding_{REGISTER_QUIET_MODE}", {})
        quiet_raw = quiet_data.get("value", 0)
        quiet_map = {0: "Off", 1: "On (Automatic)", 2: "On (Manual)"}
        quiet_mode = quiet_map.get(quiet_raw, "Unknown")
        
        # Offset-Wert aus zentraler Konfiguration
        config = self._get_offset_register_config()
        scale = config.get("scale", 1)
        
        offset_data = self.coordinator.data.get(f"{DOMAIN}_holding_{REGISTER_OFFSET}", {})
        offset_raw = offset_data.get("value", 0)
        if offset_raw > 32767:
            offset_raw = offset_raw - 65536
        offset = offset_raw * scale
        
        # Berechnete Solltemperatur für Anzeige
        current_temp = self.current_temperature
        calculated_setpoint = current_temp + offset
        
        return {
            "quiet_mode": quiet_mode,
            "offset": round(offset, 2),
            "calculated_setpoint": round(calculated_setpoint, 2),
            "current_temperature": current_temp,
            "register_config": {
                "address": REGISTER_OFFSET,
                "min_value": config.get("min_value"),
                "max_value": config.get("max_value"),
                "step": config.get("step"),
                "scale": scale
            }
        }


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup climate entities."""
    coordinator = hass.data["ha_daikin_altherma4_modbus"][entry.entry_id]
    
    entities = [
        DaikinThermostatClimate(coordinator, entry),
        DaikinDHWManualThermostat(coordinator, entry)
    ]
    
    async_add_entities(entities)
    _LOGGER.debug("Setup Daikin Thermostat Climate entities")


class DaikinDHWManualThermostat(CoordinatorEntity, ClimateEntity):
    """Climate Entity for DHW Manual Heat-up."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_dhw_manual_thermostat"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
        )
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_min_temp = 30
        self._attr_max_temp = 85
        self._attr_target_temperature_step = 1
        self._attr_icon = "mdi:water-boiler"
        self._attr_device_info = HOLDING_DEVICE_INFO
        self._attr_translation_key = "daikin_dhw_manual_thermostat"

    @property
    def hvac_mode(self):
        """Return current HVAC mode."""
        # Check DHW Single heat-up ON/OFF (Manual) - address 14
        data = self.coordinator.data.get(f"{DOMAIN}_holding_14")
        if data is None:
            return HVACMode.OFF
        
        val = data.get("value")
        return HVACMode.HEAT if val == 1 else HVACMode.OFF

    @property
    def hvac_action(self):
        """Return current HVAC action."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        
        # Check if DHW is actually running
        data = self.coordinator.data.get(f"{DOMAIN}_discrete_18")  # DHW running
        if data is None:
            return HVACAction.IDLE
        
        val = data.get("value")
        return HVACAction.HEATING if val == 1 else HVACAction.IDLE

    @property
    def current_temperature(self):
        """Return current temperature."""
        # Use DHW temperature as current temperature
        data = self.coordinator.data.get(f"{DOMAIN}_input_42")
        if data is None:
            return None
        
        # Get scale factor from const.py for DHW temperature (address 42)
        scale_factor = get_register_scale(42, INPUT_REGISTERS)
        raw_value = data.get("value")
        return raw_value * scale_factor if raw_value is not None else None

    @property
    def target_temperature(self):
        """Return target temperature."""
        # Get DHW Single heat-up setpoint (Manual) - address 15
        data = self.coordinator.data.get(f"{DOMAIN}_holding_15")
        if data is None:
            return None
        
        # Get scale factor from const.py for holding register (address 15)
        scale_factor = get_register_scale(15, HOLDING_REGISTERS)
        raw_value = data.get("value")
        return raw_value * scale_factor if raw_value is not None else None

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            # Turn ON DHW Single heat-up (Manual) - address 14
            try:
                result = await self.coordinator.client.write_register(14, 1)
                if result.isError():
                    _LOGGER.error(f"Failed to turn on DHW manual heat-up: {result}")
                else:
                    _LOGGER.debug("Successfully turned on DHW manual heat-up")
                    await self.coordinator.async_request_refresh()
            except Exception as e:
                _LOGGER.error(f"Error turning on DHW manual heat-up: {e}")
        elif hvac_mode == HVACMode.OFF:
            # Turn OFF DHW Single heat-up (Manual) - address 14
            try:
                result = await self.coordinator.client.write_register(14, 0)
                if result.isError():
                    _LOGGER.error(f"Failed to turn off DHW manual heat-up: {result}")
                else:
                    _LOGGER.debug("Successfully turned off DHW manual heat-up")
                    await self.coordinator.async_request_refresh()
            except Exception as e:
                _LOGGER.error(f"Error turning off DHW manual heat-up: {e}")

    async def async_set_temperature(self, **kwargs):
        """Set target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        
        # Get scale factor from const.py for holding register (address 15)
        scale_factor = get_register_scale(15, HOLDING_REGISTERS)
        
        # Convert temperature to raw register value
        raw_value = int(temperature / scale_factor) if scale_factor != 0 else int(temperature)
        
        # Set DHW Single heat-up setpoint (Manual) - address 15
        try:
            result = await self.coordinator.client.write_register(15, raw_value)
            if result.isError():
                _LOGGER.error(f"Failed to set DHW manual heat-up temperature: {result}")
            else:
                _LOGGER.debug(f"Successfully set DHW manual heat-up temperature to {temperature}°C (raw: {raw_value})")
                await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error setting DHW manual heat-up temperature: {e}")
