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
from .const import DOMAIN, HOLDING_DEVICE_INFO, CALCULATED_DEVICE_INFO, HOLDING_REGISTERS, INPUT_REGISTERS

_LOGGER = logging.getLogger(__name__)

def get_register_scale(address, register_list):
    """Get scale factor for a register address from const.py."""
    for register in register_list:
        if register.get("address") == address:
            return register.get("scale", 1)
    return 1  # Default scale if not found

# Register constants for Daikin Altherma 4
REGISTER_OPERATION_MODE = "input_38" # Operation mode
REGISTER_CURRENT_TEMP = "input_40" # Leaving water temperature PHE (plate heat exchanger)
REGISTER_OFFSET_HEATING = "holding_54"        # Weather-dependent mode Main LWT Heating setpoint offset
REGISTER_OFFSET_COOLING = "holding_53"        # Weather-dependent mode Main LWT Cooling setpoint offset
REGISTER_QUIET_MODE = "holding_9"     # Quiet mode operation
REGISTER_COMPRESSOR = "input_31"    # Compressor status

# DHW Control constants
REGISTER_HVAC_MODE = "holding_15"   # DHW Single heat-up ON/OFF (Manual)
REGISTER_DWH_RUNNING = "discrete_18" # DHW running status
REGISTER_DHW_TEMP = "input_43"       # DHW temperature
REGISTER_DHW_SETPOINT = "holding_16" # DHW Single heat-up setpoint (Manual)

# Fan mode constants (quiet mode)
FAN_OFF = "OFF"
FAN_AUTO = "On (Automatic)"
FAN_MANUAL = "On (Manual)"

# HVAC Mode constants
HVAC_OFF = 0
HVAC_HEAT = 1
HVAC_COOL = 2

# DHW Mode constants
DHW_OFF = 0
DHW_ON = 1

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
        self._attr_device_info = CALCULATED_DEVICE_INFO
        self._attr_translation_key = "daikin_thermostat_climate"

    def _get_offset_register_config(self):
        """Get the appropriate offset register config based on operation mode."""
        op_mode_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OPERATION_MODE}", {})
        op_mode_raw = op_mode_data.get("value", 0)
        
        # Use cooling offset when operation mode is COOL (2), otherwise heating offset
        if op_mode_raw == HVAC_COOL:
            return self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OFFSET_COOLING}", {})
        else:
            return self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OFFSET_HEATING}", {})

    @property
    def current_temperature(self):
        """Return the current temperature."""
        temp_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_CURRENT_TEMP}", {})
        temp_raw = temp_data.get("value", 0)
        temp = temp_raw * temp_data.get("scale", 0.01)  # °C
        return round(temp, 2)

    @property
    def target_temperature(self):
        """Return the current offset value as temperature."""
        # Get operation mode from input_38
        op_mode_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OPERATION_MODE}", {})
        op_mode_raw = op_mode_data.get("value", 0)
        
        # Use cooling offset when operation mode is COOL (2), otherwise heating offset
        if op_mode_raw == HVAC_COOL:
            offset_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OFFSET_COOLING}", {})
        else:
            offset_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OFFSET_HEATING}", {})
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
        quiet_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_QUIET_MODE}", {})
        quiet_raw = quiet_data.get("value", 0)
        
        fan_map = {HVAC_OFF: FAN_OFF, HVAC_HEAT: FAN_AUTO, HVAC_COOL: FAN_MANUAL}
        return fan_map.get(quiet_raw, FAN_OFF)

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return [FAN_OFF, FAN_AUTO, FAN_MANUAL]

    @property
    def hvac_mode(self):
        """Return current operation mode."""
        op_mode_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OPERATION_MODE}", {})
        op_mode_raw = op_mode_data.get("value", 0)
        
        mode_map = {HVAC_OFF: HVACMode.AUTO, HVAC_HEAT: HVACMode.HEAT, HVAC_COOL: HVACMode.COOL}
        return mode_map.get(op_mode_raw, HVACMode.AUTO)

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        comp_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_COMPRESSOR}", {})
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
        offset = max(min_temp, min(max_temp, round(temperature, 0)))
        
        # Konvertiere zu Rohwert für Holding Register
        offset_raw = int(offset)
        
        # Handle signed 16-bit integers
        if offset_raw < 0:
            offset_raw = 65536 + offset_raw

        # Get operation mode from input_38 before try block
        op_mode_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OPERATION_MODE}", {})
        op_mode_raw = op_mode_data.get("value", 0)

        try:
            # Write to the appropriate offset register based on operation mode from input_38
            if op_mode_raw == HVAC_COOL:
                await self.coordinator.client.write_register(REGISTER_OFFSET_COOLING, offset_raw)
            else:
                await self.coordinator.client.write_register(REGISTER_OFFSET_HEATING, offset_raw)
            await self.coordinator.async_request_refresh()
            _LOGGER.debug(f"Set thermostat offset to {offset}°C (raw: {offset_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set thermostat offset: {e}")

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        mode_map = {HVACMode.AUTO: HVAC_OFF, HVACMode.HEAT: HVAC_HEAT, HVACMode.COOL: HVAC_COOL}
        mode_raw = mode_map.get(hvac_mode, 0)
        
        try:
            await self.coordinator.client.write_register(REGISTER_OPERATION_MODE, mode_raw)
            await self.coordinator.async_request_refresh()
            _LOGGER.debug(f"Set HVAC mode to {hvac_mode} (raw: {mode_raw})")
        except Exception as e:
            _LOGGER.error(f"Failed to set HVAC mode: {e}")

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode (quiet mode)."""
        fan_map = {FAN_OFF: HVAC_OFF, FAN_AUTO: HVAC_HEAT, FAN_MANUAL: HVAC_COOL}
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
        quiet_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_QUIET_MODE}", {})
        quiet_raw = quiet_data.get("value", 0)
        quiet_map = {0: "Off", 1: "On (Automatic)", 2: "On (Manual)"}
        quiet_mode = quiet_map.get(quiet_raw, "Unknown")
        
        # Offset-Wert aus zentraler Konfiguration
        config = self._get_offset_register_config()
        scale = config.get("scale", 1)
        
        # Get the appropriate offset register based on operation mode from input_38
        op_mode_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OPERATION_MODE}", {})
        op_mode_raw = op_mode_data.get("value", 0)
        
        if op_mode_raw == HVAC_COOL:
            offset_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OFFSET_COOLING}", {})
        else:
            offset_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OFFSET_HEATING}", {})
        offset_raw = offset_data.get("value", 0)
        if offset_raw > 32767:
            offset_raw = offset_raw - 65536
        offset = offset_raw * scale
        
        # Berechnete Solltemperatur für Anzeige
        current_temp = self.current_temperature
        calculated_setpoint = current_temp + offset
        
        # Get operation mode from input_38 for address display
        op_mode_data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_OPERATION_MODE}", {})
        op_mode_raw = op_mode_data.get("value", 0)
        
        return {
            "quiet_mode": quiet_mode,
            "offset": round(offset, 2),
            "calculated_setpoint": round(calculated_setpoint, 2),
            "current_temperature": current_temp,
            "register_config": {
                "address": REGISTER_OFFSET_HEATING if op_mode_raw != HVAC_COOL else REGISTER_OFFSET_COOLING,
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
        self._attr_device_info = CALCULATED_DEVICE_INFO
        self._attr_translation_key = "daikin_dhw_manual_thermostat"

    @property
    def hvac_mode(self):
        data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_HVAC_MODE}")
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
        data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_DWH_RUNNING}")
        if data is None:
            return HVACAction.IDLE
        
        val = data.get("value")
        return HVACAction.HEATING if val == DHW_ON else HVACAction.IDLE

    @property
    def current_temperature(self):
        """Return current temperature."""
        # Use DHW temperature as current temperature
        data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_DHW_TEMP}")
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
        data = self.coordinator.data.get(f"{DOMAIN}_{REGISTER_DHW_SETPOINT}")
        if data is None:
            return None
        
        # Get scale factor from const.py for holding register (address 15)
        scale_factor = get_register_scale(15, HOLDING_REGISTERS)
        raw_value = data.get("value")
        return raw_value * scale_factor if raw_value is not None else None

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            try:
                result = await self.coordinator.client.write_register(15, DHW_ON)
                if result.isError():
                    _LOGGER.error(f"Failed to turn on DHW manual heat-up: {result}")
                else:
                    _LOGGER.debug("Successfully turned on DHW manual heat-up")
                    await self.coordinator.async_request_refresh()
            except Exception as e:
                _LOGGER.error(f"Error turning on DHW manual heat-up: {e}")
        elif hvac_mode == HVACMode.OFF:
            try:
                result = await self.coordinator.client.write_register(15, DHW_OFF)
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
        try:
            result = await self.coordinator.client.write_register(16, raw_value)
            if result.isError():
                _LOGGER.error(f"Failed to set DHW manual heat-up temperature: {result}")
            else:
                _LOGGER.debug(f"Successfully set DHW manual heat-up temperature to {temperature}°C (raw: {raw_value})")
                await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error setting DHW manual heat-up temperature: {e}")
