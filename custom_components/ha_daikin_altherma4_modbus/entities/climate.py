"""Climate Entity and Platform for Daikin Altherma 4 Modbus integration."""

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..common import (
    RegisterVersionDeviceInfoMixin,
    get_coordinator_register_data,
    get_register_scale,
    get_register_value,
    is_entity_available,
    is_unavailable_value,
    safe_write_register,
    to_unsigned_16bit,
)
from ..core.const import (
    DHW_OFF,
    DHW_ON,
    DOMAIN,
    FAN_AUTO,
    FAN_MANUAL,
    FAN_OFF,
    HVAC_COOL,
    HVAC_HEAT,
    HVAC_OFF,
    REGISTER_COMPRESSOR,
    REGISTER_CURRENT_TEMP,
    REGISTER_DHW_BOOSTER_HVAC_MODE,
    REGISTER_DHW_BOOSTER_RUNNING,
    REGISTER_DHW_BOOSTER_SETPOINT,
    REGISTER_DHW_BOOSTER_TEMP,
    REGISTER_DHW_HVAC_MODE,
    REGISTER_DHW_RUNNING,
    REGISTER_DHW_SETPOINT,
    REGISTER_DHW_TEMP,
    REGISTER_MAIN_ZONE_RUNNING,
    REGISTER_MAIN_ZONE_SWITCH,
    REGISTER_OFFSET_COOLING,
    REGISTER_OFFSET_HEATING,
    REGISTER_OPERATION_MODE,
    REGISTER_QUIET_MODE,
    REGISTER_ROOM_COOLING_MAX,
    REGISTER_ROOM_COOLING_MIN,
    REGISTER_ROOM_COOLING_SETPOINT_FINE,
    REGISTER_ROOM_HEATING_MAX,
    REGISTER_ROOM_HEATING_MIN,
    REGISTER_ROOM_HEATING_SETPOINT_FINE,
    REGISTER_ROOM_OPERATION_MODE_ACTUAL,
    REGISTER_ROOM_TEMP_MAIN,
)
from ..core.register_constants import (
    CALCULATED_DEVICE_INFO,
    HOLDING_REGISTERS,
    INPUT_REGISTERS,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0  # Managed by DataUpdateCoordinator


class DaikinThermostatClimate(
    RegisterVersionDeviceInfoMixin, CoordinatorEntity, ClimateEntity
):
    """Climate Entity for Daikin Altherma 4 Thermostat Control."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

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

    @property
    def available(self) -> bool:
        """Return True if the core climate registers report valid values."""
        data = self.coordinator.data
        return is_entity_available(
            data, REGISTER_OPERATION_MODE
        ) and is_entity_available(data, REGISTER_CURRENT_TEMP)

    def _get_register_data(self, register_name):
        """Get register data without DOMAIN prefix."""
        return get_coordinator_register_data(self.coordinator, register_name)

    def _get_operation_mode(self):
        """Get the current operation mode value (None if unavailable)."""
        op_mode_data = self._get_register_data(f"{DOMAIN}_{REGISTER_OPERATION_MODE}")
        val = get_register_value(op_mode_data)
        if val is None or is_unavailable_value(val):
            return None
        return val

    def _get_offset_register_config(self):
        """Get the appropriate offset register config based on operation mode."""
        op_mode_raw = self._get_operation_mode()

        # Use cooling offset when operation mode is COOL (2), otherwise heating offset
        # (None/unavailable defaults to heating so min/max/step stay resolvable).
        if op_mode_raw == HVAC_COOL:
            return self._get_register_data(f"{DOMAIN}_{REGISTER_OFFSET_COOLING}")
        else:
            return self._get_register_data(f"{DOMAIN}_{REGISTER_OFFSET_HEATING}")

    @property
    def current_temperature(self):
        """Return the current temperature (None if unavailable)."""
        temp_data = self._get_register_data(f"{DOMAIN}_{REGISTER_CURRENT_TEMP}")
        temp_raw = get_register_value(temp_data)
        if temp_raw is None or is_unavailable_value(temp_raw):
            return None

        # Value is already scaled by data_manager (mapping_transform never
        # scales specials, so a stored 32766 stays detectable above).
        return round(float(temp_raw), 2)

    @property
    def target_temperature(self):
        """Return the current offset value as temperature."""
        offset_data = self._get_offset_data()
        if offset_data is None or offset_data["offset"] is None:
            return None
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
        offset_raw = get_register_value(offset_data)
        if offset_raw is None or is_unavailable_value(offset_raw):
            return None

        # Get scale from centralized config (always needed for return value)
        config = self._get_offset_register_config()

        # Value is already scaled by data_manager (specials stay raw, see above).
        offset = float(offset_raw)
        scale = get_register_scale(offset_data)

        return {
            "op_mode_raw": op_mode_raw,
            "offset_raw": offset_raw,
            "offset": offset,
            "scale": scale,
            "config": config,
        }

    def _get_offset_static_config(self):
        """Get the static config for offset register from const.py."""
        op_mode_raw = self._get_operation_mode()
        # Use cooling offset when operation mode is COOL (2), otherwise heating offset
        register_name = (
            REGISTER_OFFSET_COOLING
            if op_mode_raw == HVAC_COOL
            else REGISTER_OFFSET_HEATING
        )
        for register in HOLDING_REGISTERS:
            if register.register_name == register_name:
                return register
        return None

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature from const.py."""
        config = self._get_offset_static_config()
        return float(config.step if config else 0.1)

    @property
    def min_temp(self):
        """Return the minimum offset value from const.py."""
        config = self._get_offset_static_config()
        return float(config.min_value if config else -5)

    @property
    def max_temp(self):
        """Return the maximum offset value from const.py."""
        config = self._get_offset_static_config()
        return float(config.max_value if config else 5)

    @property
    def fan_mode(self):
        """Return the current fan mode (quiet mode)."""
        quiet_data = self._get_register_data(f"{DOMAIN}_{REGISTER_QUIET_MODE}")
        quiet_raw = get_register_value(quiet_data)
        if quiet_raw is None or is_unavailable_value(quiet_raw):
            return FAN_OFF

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
        comp_raw = get_register_value(comp_data)
        if comp_raw is None or is_unavailable_value(comp_raw):
            return HVACAction.IDLE

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
            _LOGGER.warning(
                "async_set_temperature called without temperature parameter"
            )
            return

        # Get limits from register configuration
        config = self._get_offset_static_config()
        min_temp = float(config.min_value if config else -5)
        max_temp = float(config.max_value if config else 5)
        offset = max(min_temp, min(max_temp, round(temperature, 0)))

        # Konvertiere zu Rohwert für Holding Register
        offset_raw = int(offset)

        # Convert signed integer to unsigned 16-bit safely
        offset_raw = to_unsigned_16bit(offset_raw)

        # Get operation mode directly: the write target depends only on the
        # mode, not on the current offset value (which may be unavailable).
        op_mode_raw = self._get_operation_mode()
        if op_mode_raw is None:
            _LOGGER.debug(
                "Skipping thermostat offset write: operation mode unavailable"
            )
            return

        if op_mode_raw == HVAC_COOL:
            await safe_write_register(
                self.coordinator.data_manager.write_holding_register,
                REGISTER_OFFSET_COOLING,
                offset_raw,
                operation_name="set",
                register_type="thermostat offset",
                coordinator=self.coordinator,
            )
        else:
            await safe_write_register(
                self.coordinator.data_manager.write_holding_register,
                REGISTER_OFFSET_HEATING,
                offset_raw,
                operation_name="set",
                register_type="thermostat offset",
                coordinator=self.coordinator,
            )
        _LOGGER.debug(f"Set thermostat offset to {offset}°C (raw: {offset_raw})")

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

        await safe_write_register(
            self.coordinator.data_manager.write_holding_register,
            REGISTER_OPERATION_MODE,
            mode_raw,
            operation_name="set",
            register_type="HVAC mode",
            coordinator=self.coordinator,
        )
        _LOGGER.debug(f"Set HVAC mode to {hvac_mode} (raw: {mode_raw})")

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode (quiet mode)."""
        # Keep write mapping aligned with const.SELECT_REGISTERS enum_map for holding_9.
        fan_map = {FAN_OFF: 0, FAN_AUTO: 1, FAN_MANUAL: 2}
        mode_raw = fan_map.get(fan_mode, 0)

        await safe_write_register(
            self.coordinator.data_manager.write_holding_register,
            REGISTER_QUIET_MODE,
            mode_raw,
            operation_name="set",
            register_type="fan mode",
            coordinator=self.coordinator,
        )
        _LOGGER.debug(f"Set fan mode to {fan_mode} (raw: {mode_raw})")

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        quiet_data = self._get_register_data(f"{DOMAIN}_{REGISTER_QUIET_MODE}")
        quiet_raw = get_register_value(quiet_data)
        quiet_map = {0: "Off", 1: "On (Automatic)", 2: "On (Manual)"}
        quiet_mode = quiet_map.get(quiet_raw, "Unknown")

        # Get offset data using helper method
        offset_data_info = self._get_offset_data()
        if offset_data_info is None:
            return {
                "quiet_mode": quiet_mode,
                "offset": None,
                "calculated_setpoint": None,
                "current_temperature": self.current_temperature,
            }
        offset = offset_data_info["offset"]
        op_mode_raw = offset_data_info["op_mode_raw"]
        config = offset_data_info["config"]

        # Berechnete Solltemperatur für Anzeige
        current_temp = self.current_temperature
        calculated_setpoint = (
            round(current_temp + offset, 2)
            if current_temp is not None and offset is not None
            else None
        )

        return {
            "quiet_mode": quiet_mode,
            "offset": round(offset, 2),
            "calculated_setpoint": round(calculated_setpoint, 2),
            "current_temperature": current_temp,
            "register_config": {
                "address": REGISTER_OFFSET_HEATING
                if op_mode_raw != HVAC_COOL
                else REGISTER_OFFSET_COOLING,
                "min_value": config.get("min_value")
                if isinstance(config, dict)
                else getattr(config, "min_value", None),
                "max_value": config.get("max_value")
                if isinstance(config, dict)
                else getattr(config, "max_value", None),
                "step": config.get("step")
                if isinstance(config, dict)
                else getattr(config, "step", None),
                "scale": offset_data_info["scale"],
            },
        }

    async def async_turn_on(self):
        """Turn thermostat control on (mapped to AUTO mode)."""
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self):
        """Compatibility path for turn_off; this thermostat has no native OFF."""
        await self.async_set_hvac_mode(HVACMode.AUTO)


class DaikinRoomThermostatMainClimate(
    RegisterVersionDeviceInfoMixin, CoordinatorEntity, ClimateEntity
):
    """Climate Entity for the Main-zone room thermostat (issue #94).

    Display and adjust the room thermostat setpoint. The Daikin Altherma
    remains responsible for the actual heating control; Home Assistant
    only changes the room setpoint the Daikin uses.

    - Current temperature: ``input_50`` (remote controller room temp, Main)
    - Target temperature: ``holding_76`` (heat) / ``holding_77`` (cool),
      Temp16 fine setpoints written as ``round(temp / scale)`` (x100)
    - Limits: ``input_84/85`` (heat) / ``input_86/87`` (cool), catalog fallback
    - On/Off: ``coil_2`` — OFF physically disables the main zone
    - Action: ``discrete_20`` (main zone running)
    """

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.coordinator: Any = coordinator
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_room_thermostat_main_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
        self._attr_device_info = CALCULATED_DEVICE_INFO
        self._attr_translation_key = "daikin_room_thermostat_main_climate"

    def _get_register_data(self, register_name):
        """Get register data without DOMAIN prefix."""
        return get_coordinator_register_data(self.coordinator, register_name)

    def _get_register_value(self, register_name):
        """Get scaled register value (None if missing/unavailable)."""
        data = self._get_register_data(f"{DOMAIN}_{register_name}")
        val = get_register_value(data)
        if val is None or is_unavailable_value(val):
            return None
        return val

    def _is_cool_mode(self) -> bool:
        """Return True when the unit operates in cooling mode.

        Prefers the read-only actual state (``input_38``), falls back to
        the configured mode (``holding_3``). Unknown/Auto defaults to heat.
        """
        actual = self._get_register_value(REGISTER_ROOM_OPERATION_MODE_ACTUAL)
        if actual == HVAC_COOL:
            return True
        if actual == HVAC_HEAT:
            return False
        configured = self._get_register_value(REGISTER_OPERATION_MODE)
        return configured == HVAC_COOL

    def _active_setpoint_register(self) -> str:
        """Return the setpoint register for the current mode."""
        if self._is_cool_mode():
            return REGISTER_ROOM_COOLING_SETPOINT_FINE
        return REGISTER_ROOM_HEATING_SETPOINT_FINE

    def _static_holding_config(self, register_name):
        """Return the static HOLDING_REGISTERS config for a register."""
        for register in HOLDING_REGISTERS:
            if register.register_name == register_name:
                return register
        return None

    def _get_limits(self) -> tuple[float, float, float]:
        """Return (min, max, step) for the active mode.

        Limits come from the device limit inputs (84/85 heat, 86/87 cool);
        min/max/step fall back to the static holding_76/77 catalog config.
        """
        if self._is_cool_mode():
            min_reg, max_reg = REGISTER_ROOM_COOLING_MIN, REGISTER_ROOM_COOLING_MAX
            setpoint_reg = REGISTER_ROOM_COOLING_SETPOINT_FINE
        else:
            min_reg, max_reg = REGISTER_ROOM_HEATING_MIN, REGISTER_ROOM_HEATING_MAX
            setpoint_reg = REGISTER_ROOM_HEATING_SETPOINT_FINE

        config = self._static_holding_config(setpoint_reg)
        fallback_min = float(config.min_value if config else 12)
        fallback_max = float(config.max_value if config else 30)

        min_val = self._get_register_value(min_reg)
        max_val = self._get_register_value(max_reg)
        try:
            min_temp = float(min_val) if min_val is not None else fallback_min
            max_temp = float(max_val) if max_val is not None else fallback_max
        except (ValueError, TypeError):
            min_temp, max_temp = fallback_min, fallback_max
        if min_temp >= max_temp:
            min_temp, max_temp = fallback_min, fallback_max
        step = float(config.step if config else 0.5)
        return min_temp, max_temp, step

    @property
    def available(self) -> bool:
        """Return True if room temp and the active setpoint are valid."""
        data = self.coordinator.data
        return is_entity_available(data, REGISTER_ROOM_TEMP_MAIN) and (
            is_entity_available(data, REGISTER_ROOM_HEATING_SETPOINT_FINE)
            or is_entity_available(data, REGISTER_ROOM_COOLING_SETPOINT_FINE)
        )

    @property
    def current_temperature(self):
        """Return the measured room temperature (input_50)."""
        temp = self._get_register_value(REGISTER_ROOM_TEMP_MAIN)
        if temp is None:
            return None
        return round(float(temp), 2)

    @property
    def target_temperature(self):
        """Return the room setpoint for the current mode."""
        setpoint = self._get_register_value(self._active_setpoint_register())
        if setpoint is None:
            return None
        return round(float(setpoint), 2)

    @property
    def target_temperature_step(self):
        """Return the step from the register catalog."""
        return self._get_limits()[2]

    @property
    def min_temp(self):
        """Return the device lower limit (or catalog fallback)."""
        return self._get_limits()[0]

    @property
    def max_temp(self):
        """Return the device upper limit (or catalog fallback)."""
        return self._get_limits()[1]

    def _is_main_zone_on(self) -> bool:
        """Return True if the main zone is enabled (coil_2)."""
        val = self._get_register_value(REGISTER_MAIN_ZONE_SWITCH)
        if val is None:
            return False
        return bool(val)

    @property
    def hvac_mode(self):
        """Return OFF when the zone is disabled, else HEAT/COOL by mode."""
        if not self._is_main_zone_on():
            return HVACMode.OFF
        if self._is_cool_mode():
            return HVACMode.COOL
        return HVACMode.HEAT

    @property
    def hvac_action(self):
        """Return HEATING/COOLING while the zone runs, else IDLE/OFF."""
        mode = self.hvac_mode
        if mode == HVACMode.OFF:
            return HVACAction.OFF
        running = self._get_register_value(REGISTER_MAIN_ZONE_RUNNING)
        if running:
            return HVACAction.COOLING if mode == HVACMode.COOL else HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs):
        """Write the room setpoint (Temp16, scaled x100)."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            _LOGGER.warning(
                "async_set_temperature called without temperature parameter"
            )
            return

        setpoint_register = self._active_setpoint_register()
        min_temp, max_temp, step = self._get_limits()
        clamped = max(min_temp, min(max_temp, float(temperature)))
        if step and step > 0:
            clamped = round(round(clamped / step) * step, 2)

        data = self._get_register_data(f"{DOMAIN}_{setpoint_register}")
        scale = get_register_scale(data) or 1
        raw_value = round(clamped / scale) if scale else int(clamped)

        await safe_write_register(
            self.coordinator.data_manager.write_holding_register,
            setpoint_register,
            raw_value,
            operation_name="set",
            register_type="room thermostat setpoint",
            coordinator=self.coordinator,
        )
        _LOGGER.debug(f"Set room thermostat setpoint to {clamped}°C (raw: {raw_value})")

    async def async_set_hvac_mode(self, hvac_mode):
        """Enable/disable the main zone and select heat/cool.

        OFF only switches coil_2 off (and physically disables the zone);
        HEAT/COOL enable the zone and set the operation mode (holding_3).
        The holding_3 write is skipped on heat-only devices where the
        register reports unavailable.
        """
        if hvac_mode == HVACMode.OFF:
            await safe_write_register(
                self.coordinator.data_manager.write_coil_register,
                REGISTER_MAIN_ZONE_SWITCH,
                False,
                operation_name="turn off",
                register_type="main zone",
                coordinator=self.coordinator,
            )
            _LOGGER.debug("Turned main zone off (coil_2)")
            return

        if hvac_mode not in (HVACMode.HEAT, HVACMode.COOL):
            _LOGGER.warning(f"Unsupported HVAC mode for room thermostat: {hvac_mode}")
            return

        await safe_write_register(
            self.coordinator.data_manager.write_coil_register,
            REGISTER_MAIN_ZONE_SWITCH,
            True,
            operation_name="turn on",
            register_type="main zone",
            coordinator=self.coordinator,
        )
        if self._get_register_value(REGISTER_OPERATION_MODE) is None:
            _LOGGER.debug(
                "Skipping operation mode write: holding_3 unavailable "
                "(e.g. heat-only device)"
            )
            return
        await safe_write_register(
            self.coordinator.data_manager.write_holding_register,
            REGISTER_OPERATION_MODE,
            HVAC_COOL if hvac_mode == HVACMode.COOL else HVAC_HEAT,
            operation_name="set",
            register_type="operation mode",
            coordinator=self.coordinator,
        )
        _LOGGER.debug(f"Set room thermostat HVAC mode to {hvac_mode}")

    @property
    def extra_state_attributes(self):
        """Return diagnostic attributes for the room thermostat."""
        return {
            "room_temperature": self.current_temperature,
            "setpoint_register": self._active_setpoint_register(),
            "min_limit": self.min_temp,
            "max_limit": self.max_temp,
            "main_zone_enabled": self._is_main_zone_on(),
            "main_zone_running": self._get_register_value(REGISTER_MAIN_ZONE_RUNNING),
            "compressor_running": self._get_register_value(REGISTER_COMPRESSOR),
            "operation_mode_actual": self._get_register_value(
                REGISTER_ROOM_OPERATION_MODE_ACTUAL
            ),
        }

    async def async_turn_on(self):
        """Turn the main zone on (mapped to HEAT)."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn the main zone off (coil_2 OFF)."""
        await self.async_set_hvac_mode(HVACMode.OFF)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup climate entities."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator

    entities = [
        DaikinThermostatClimate(coordinator, entry),
        DaikinRoomThermostatMainClimate(coordinator, entry),
        DaikinDHWThermostat(coordinator, entry, dhw_type="manual"),
        DaikinDHWThermostat(coordinator, entry, dhw_type="booster"),
    ]

    async_add_entities(entities)
    _LOGGER.debug("Setup Daikin Thermostat Climate entities")


class DaikinDHWThermostat(
    RegisterVersionDeviceInfoMixin, CoordinatorEntity, ClimateEntity
):
    """Climate Entity for DHW Heat-up (Manual or Booster)."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(self, coordinator, entry, dhw_type="manual"):
        super().__init__(coordinator)
        # Type hint to indicate coordinator has data_manager attribute
        self.coordinator: Any = coordinator  # Coordinator with data_manager attribute
        self._entry = entry
        self._dhw_type = dhw_type

        # Set registers based on DHW type
        if dhw_type == "booster":
            self._hvac_mode_register = REGISTER_DHW_BOOSTER_HVAC_MODE
            self._running_register = REGISTER_DHW_BOOSTER_RUNNING
            self._temp_register = REGISTER_DHW_BOOSTER_TEMP
            self._setpoint_register = REGISTER_DHW_BOOSTER_SETPOINT
            self._unique_id_suffix = "dhw_booster_thermostat"
            self._translation_key = "daikin_dhw_booster_thermostat"
            self._write_register_func = (
                self.coordinator.data_manager.write_holding_register
            )
        else:  # manual
            self._hvac_mode_register = REGISTER_DHW_HVAC_MODE
            self._running_register = REGISTER_DHW_RUNNING
            self._temp_register = REGISTER_DHW_TEMP
            self._setpoint_register = REGISTER_DHW_SETPOINT
            self._unique_id_suffix = "dhw_manual_thermostat"
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
        self._attr_target_temperature_step = 1
        self._attr_device_info = CALCULATED_DEVICE_INFO
        self._attr_translation_key = self._translation_key

    @property
    def available(self) -> bool:
        """Return True if the hvac mode and temp registers report valid values."""
        data = self.coordinator.data
        return is_entity_available(
            data, self._hvac_mode_register
        ) and is_entity_available(data, self._temp_register)

    def _get_register_data(self, register_name):
        """Get register data without DOMAIN prefix."""
        return get_coordinator_register_data(self.coordinator, register_name)

    def _get_register_value(self, register_name, register_type):
        """Get scaled value from a register (None if unavailable).

        Values are already scaled by data_manager; specials are stored raw
        (mapping_transform never scales them) and detected here centrally.
        """
        data = self._get_register_data(f"{DOMAIN}_{register_name}")
        if data is None:
            return None

        raw_value = get_register_value(data)
        if raw_value is None or is_unavailable_value(raw_value):
            return None
        return raw_value

    @property
    def hvac_mode(self):
        data = self._get_register_data(f"{DOMAIN}_{self._hvac_mode_register}")
        if data is None:
            return HVACMode.OFF

        val = get_register_value(data)
        if val is None or is_unavailable_value(val):
            return HVACMode.OFF
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

        val = get_register_value(data)
        if val is None or is_unavailable_value(val):
            return HVACAction.IDLE
        return HVACAction.HEATING if val == DHW_ON else HVACAction.IDLE

    @property
    def current_temperature(self):
        """Return current temperature."""
        # Use DHW temperature as current temperature
        return self._get_register_value(self._temp_register, INPUT_REGISTERS)

    @property
    def target_temperature(self):
        """Return target temperature."""
        return self._get_register_value(self._setpoint_register, HOLDING_REGISTERS)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            await safe_write_register(
                self._write_register_func,
                self._hvac_mode_register,
                DHW_ON,
                operation_name="turn on",
                register_type=f"{self._dhw_type} DHW heat-up",
                coordinator=self.coordinator,
            )
            _LOGGER.debug(f"Successfully turned on {self._dhw_type} DHW heat-up")
        elif hvac_mode == HVACMode.OFF:
            await safe_write_register(
                self._write_register_func,
                self._hvac_mode_register,
                DHW_OFF,
                operation_name="turn off",
                register_type=f"{self._dhw_type} DHW heat-up",
                coordinator=self.coordinator,
            )
            _LOGGER.debug(f"Successfully turned off {self._dhw_type} DHW heat-up")

    async def async_set_temperature(self, **kwargs):
        """Set target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        # Get scale factor from register config for DHW setpoint
        data = self._get_register_data(f"{DOMAIN}_{self._setpoint_register}")
        scale_factor = get_register_scale(data)

        # Convert temperature to raw register value
        raw_value = (
            int(temperature / scale_factor) if scale_factor != 0 else int(temperature)
        )
        await safe_write_register(
            self.coordinator.data_manager.write_holding_register,
            self._setpoint_register,
            raw_value,
            operation_name="set",
            register_type=f"{self._dhw_type} DHW temperature",
            coordinator=self.coordinator,
        )
        _LOGGER.debug(
            f"Successfully set {self._dhw_type} DHW heat-up temperature to {temperature}°C (raw: {raw_value})"
        )

    async def async_turn_on(self):
        """Turn on DHW heat-up."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn off DHW heat-up."""
        await self.async_set_hvac_mode(HVACMode.OFF)
