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
from .const import DOMAIN, DEVICE_INFO, HOLDING_REGISTERS

_LOGGER = logging.getLogger(__name__)

# Register constants for Daikin Altherma 4
REGISTER_CURRENT_TEMP = 40  # Leaving water temperature BUH
REGISTER_OFFSET = 53        # Weather-dependent mode Main LWT Heating setpoint offset
REGISTER_OPERATION_MODE = 2  # Operation mode
REGISTER_QUIET_MODE = 8     # Quiet mode operation
REGISTER_COMPRESSOR = 30    # Compressor status

# Fan mode constants (quiet mode)
FAN_OFF = "OFF"
FAN_AUTO = "On (Automatic)"
FAN_MANUAL = "On (Manual)"

class DaikinThermostatClimate(CoordinatorEntity, ClimateEntity):
    """Climate Entity for Daikin Altherma 4 Thermostat Control."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Daikin Thermostat Control"
        self._attr_unique_id = f"{DOMAIN}_thermostat_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        )
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
        self._attr_device_info = DEVICE_INFO

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
        return round(temp, 1)

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
            _LOGGER.info(f"Set thermostat offset to {offset}°C (raw: {offset_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set thermostat offset: {e}")

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        mode_map = {HVACMode.AUTO: 0, HVACMode.HEAT: 1, HVACMode.COOL: 2}
        mode_raw = mode_map.get(hvac_mode, 0)
        
        try:
            await self.coordinator.client.write_register(REGISTER_OPERATION_MODE, mode_raw)
            await self.coordinator.async_request_refresh()
            _LOGGER.info(f"Set HVAC mode to {hvac_mode} (raw: {mode_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set HVAC mode: {e}")

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode (quiet mode)."""
        fan_map = {FAN_OFF: 0, FAN_AUTO: 1, FAN_MANUAL: 2}
        mode_raw = fan_map.get(fan_mode, 0)
        
        try:
            await self.coordinator.client.write_register(REGISTER_QUIET_MODE, mode_raw)
            await self.coordinator.async_request_refresh()
            _LOGGER.info(f"Set fan mode to {fan_mode} (raw: {mode_raw})")
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
            "offset": round(offset, 1),
            "calculated_setpoint": round(calculated_setpoint, 1),
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
        DaikinThermostatClimate(coordinator, entry)
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Setup Daikin Thermostat Climate entity")
