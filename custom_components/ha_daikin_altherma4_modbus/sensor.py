import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .common import (
    get_register_value,
    is_entity_available,
    is_unavailable_value,
)
from .config_entry_utils import entry_value
from .const import DOMAIN, SPECIAL_REGISTER_NOT_SUPPORTED
from .register_constants import (
    CALCULATED_DEVICE_INFO,
    CALCULATED_SENSORS,
    INPUT_DEVICE_INFO,
    INPUT_REGISTERS,
)
from .register_types import TEXT16
from .repair import (
    async_create_abnormality_issue,
    async_delete_abnormality_issue,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0  # Managed by DataUpdateCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup aller Sensors über Config Entry."""
    from .common import get_coordinator_from_entry

    unified_coordinator = get_coordinator_from_entry(hass, entry)
    if unified_coordinator is None:
        return
    entities = []

    # Input-Register Sensoren (nur ohne device_class running/problem)
    for item in INPUT_REGISTERS:
        device_class = item.device_class
        if device_class in ["running", "problem"]:
            continue  # Nur als Binärsensoren erstellen

        address = item.address
        register_name = item.register_name

        # Skip registers that returned 32767 (not supported by device)
        reg_data = unified_coordinator.data.get(register_name)
        if reg_data is not None:
            val = get_register_value(reg_data)
            if val is not None and val == SPECIAL_REGISTER_NOT_SUPPORTED:
                _LOGGER.debug(
                    "Skipping sensor %s (address %d): register not supported (32767)",
                    register_name,
                    address,
                )
                continue
        unit = item.unit or ""
        count = item.count or 1
        enum_map = item.enum_map
        entity_category = item.entity_category
        unique_id = item.unique_id or f"{DOMAIN}_{register_name}"
        translation_key = item.translation_key

        data_type = item.data_type

        entities.append(
            DaikinInputSensor(
                coordinator=unified_coordinator,
                entry=entry,
                address=address,
                unit=unit,
                data_type=data_type,
                count=count,
                enum_map=enum_map,
                register_name=register_name,
                device_class=item.device_class,
                entity_category=entity_category,
                unique_id=unique_id,
                translation_key=translation_key,
                device_info=INPUT_DEVICE_INFO,
                state_class=item.state_class,
            )
        )
        _LOGGER.debug(f"unique_id: {unique_id} - translation_key {translation_key}")

    # Externer elektrischer Leistungssensor (immer erstellen, Verfügbarkeit wird über available property gesteuert)
    _LOGGER.debug("Creating External Electric Power Sensor")
    entities.append(
        ExternalElectricPowerSensor(
            coordinator=unified_coordinator,
            entry=entry,
            unique_id=f"{DOMAIN}_external_electric_power",
            unit="W",
            device_class="power",
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="external_electric_power",
            device_info=INPUT_DEVICE_INFO,
        )
    )

    # Berechnete Sensoren
    _LOGGER.debug(f"Processing {len(CALCULATED_SENSORS)} calculated sensors")
    for calc in CALCULATED_SENSORS:
        _LOGGER.debug(
            f"Processing calculated sensor: {calc.name} (type: {calc.calc_type})"
        )
        if calc.calc_type == "heat_power":
            entities.append(
                ThermalHeatOutput(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc.register_name,
                    unit=calc.unit,
                    device_class=calc.device_class,
                    entity_category=calc.entity_category,
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.translation_key,
                )
            )
        elif calc.calc_type == "cop":
            entities.append(
                CalculatedCoPSensor(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc.register_name,
                    unit=calc.unit,
                    device_class=calc.device_class,
                    entity_category=calc.entity_category,
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.translation_key,
                )
            )
        elif calc.calc_type == "last_triggered":
            entities.append(
                LastTriggeredSensor(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc.register_name,
                    unit=calc.unit,
                    device_class=calc.device_class,
                    trigger_register_name=calc.trigger_register_name,
                    entity_category=calc.entity_category,
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.translation_key,
                )
            )
        elif calc.calc_type == "delta_t":
            entities.append(
                DeltaTSensor(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc.register_name,
                    unit=calc.unit,
                    device_class=calc.device_class,
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.translation_key,
                )
            )

    async_add_entities(entities)

    # Set up abnormality monitoring callback
    _abnormality_state = {"issue_created": False}

    def _check_abnormality():
        """Check input_21 (Unit abnormality) and create/delete repair issue."""
        data = unified_coordinator.data.get("input_21")
        if data is None:
            return
        val = get_register_value(data)
        if val is None:
            return

        # Get abnormality code and sub code for the issue message
        code_data = unified_coordinator.data.get("input_22")
        code_val = get_register_value(code_data) if code_data else None
        sub_code_data = unified_coordinator.data.get("input_23")
        sub_code_val = get_register_value(sub_code_data) if sub_code_data else None

        if val in (1, 2) and not _abnormality_state["issue_created"]:
            # fault=1 or warning=2
            async_create_abnormality_issue(
                hass,
                entry,
                abnormality_code=str(code_val) if code_val is not None else "unknown",
                abnormality_sub_code=int(sub_code_val)
                if sub_code_val is not None
                else 0,
            )
            _abnormality_state["issue_created"] = True
        elif val == 0 and _abnormality_state["issue_created"]:
            # no_error=0 - delete the issue
            async_delete_abnormality_issue(hass, entry)
            _abnormality_state["issue_created"] = False

    unified_coordinator.async_add_listener(_check_abnormality)


class DaikinInputSensor(CoordinatorEntity, SensorEntity):
    """A Sensor for Input-Register."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        address,
        unit,
        data_type,
        count,
        enum_map,
        register_name,
        device_class=None,
        entity_category=None,
        unique_id=None,
        device_info=None,
        translation_key=None,
        state_class=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._data_type = data_type
        # Scale only from register_types (data_type.scaling)
        self._scale = getattr(data_type, "scaling", 1) if data_type else 1
        self._count = count
        self._enum_map = enum_map
        self._attr_register_name = register_name
        self._attr_unique_id = unique_id
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key

        # Enum sensors: special configuration
        if enum_map:
            self._attr_force_update = True
            # Clear unit of measurement for enum sensors (they are not numeric)
            self._attr_native_unit_of_measurement = None
            # Store possible values in extra_state_attributes
            self._attr_extra_state_attributes = {
                "possible_values": list(enum_map.values())
            }
        else:
            # Numeric sensors: enable long-term statistics
            # Use register-defined state_class if specified, otherwise default to MEASUREMENT
            if state_class:
                self._attr_state_class = state_class
            else:
                self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return is_entity_available(self.coordinator.data, self._attr_register_name)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data.get(self._attr_register_name)
        if data is None:
            return None
        val = get_register_value(data)
        if val is None:
            return None

        # Handle string data types directly
        if self._data_type is TEXT16:
            return str(val) if val is not None else None

        # Convert to appropriate type based on sensor characteristics
        try:
            # For scaled sensors, keep as float to preserve decimal places
            scale = getattr(self._data_type, "scaling", 1) if self._data_type else 1
            if scale != 1:
                val = float(val)
            else:
                val = int(val)
        except (ValueError, TypeError):
            return None

        # Return None for unavailable value (32765 or 32766)
        if is_unavailable_value(val):
            return None

        # ENUM Mapping
        if self._enum_map:
            mapped_value = self._enum_map.get(val)
            if mapped_value is not None:
                return mapped_value  # Return string value directly, no scaling
            else:
                # For enum sensors, if value not found in map, return "Unknown"
                _LOGGER.warning(
                    f"Enum sensor {self._attr_unique_id} - value {val} not in enum_map {self._enum_map}"
                )
                return "Unknown"

        # Value is already scaled by data_manager
        # Auf 2 Nachkommastellen runden bei °C Sensoren
        if self._attr_native_unit_of_measurement == "°C":
            return round(val, 2)

        return val


def calculate_thermal_heat_output(coordinator):
    """Berechnet die thermische Leistung in W."""
    from .const import (
        REGISTER_FLOW_RATE,
        REGISTER_LEAVING_WATER_TEMP,
        REGISTER_RETURN_WATER_TEMP,
    )

    # Flow, Vorlauf- und Rücklauftemperatur aus den Input-Sensoren (bereits skaliert)
    flow_data = coordinator.data.get(REGISTER_FLOW_RATE, {})
    flow_raw = get_register_value(flow_data) or 0  # Flow rate in L/min
    temp_vl_data = coordinator.data.get(REGISTER_LEAVING_WATER_TEMP, {})
    temp_vl_raw = (
        get_register_value(temp_vl_data) or 0
    )  # Leaving water temperature PHE in °C
    temp_rl_data = coordinator.data.get(REGISTER_RETURN_WATER_TEMP, {})
    temp_rl_raw = (
        get_register_value(temp_rl_data) or 0
    )  # Return water temperature in °C

    # Values from coordinator are already scaled by data_manager
    flow = flow_raw  # L/min
    temp_vl = temp_vl_raw  # °C
    temp_rl = temp_rl_raw  # °C

    delta_t = temp_vl - temp_rl
    # Use absolute value to correctly calculate thermal power in both heating
    # (vl > rl) and cooling (vl < rl) mode
    thermal_heat_output = (
        flow * abs(delta_t) * 70
    )  # Berechnung thermische Leistung in W
    _LOGGER.debug(f"flow: {flow} L/min")
    _LOGGER.debug(f"delta_t: {delta_t} K")
    _LOGGER.debug(f"thermal_heat_output: {thermal_heat_output} W")
    return round(thermal_heat_output, 2)


class ThermalHeatOutput(CoordinatorEntity, SensorEntity):
    """Berechneter Sensor für Wärmepumpenleistung."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        unit,
        device_class,
        entity_category=None,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_translation_key = translation_key
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._restored_value = None

    def _calculate_thermal_heat_output(self):
        """Berechnet die thermische Leistung in W."""
        return calculate_thermal_heat_output(self.coordinator)

    @property
    def native_value(self):
        """Berechnet die thermische Leistung in W."""
        return self._calculate_thermal_heat_output()


class CalculatedCoPSensor(CoordinatorEntity, SensorEntity):
    """Berechneter Sensor für Coefficient of Performance (CoP)."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        unit,
        device_class,
        entity_category=None,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_translation_key = translation_key

    def _calculate_thermal_heat_output(self):
        """Berechnet die thermische Leistung in W."""
        return calculate_thermal_heat_output(self.coordinator)

    @property
    def native_value(self):
        """Berechnet den CoP als Verhältnis von Heizleistung zu elektrischer Leistung."""
        # Heizleistung aus der gleichen Berechnung wie ThermalHeatOutput
        heat_power = self._calculate_thermal_heat_output()  # in W

        # Elektrische Leistung
        electric_power_sensor = entry_value(self._entry, "electric_power_sensor")
        if electric_power_sensor:
            # Externer Sensor
            state = self.coordinator.hass.states.get(electric_power_sensor)
            unit = (
                getattr(state, "attributes", {}).get("unit_of_measurement")
                if state
                else None
            )
            if state and state.state not in [None, "unknown", "unavailable"]:
                try:
                    if unit == "kW":
                        electric_power = float(state.state) * 1000
                    else:
                        electric_power = float(state.state)
                except ValueError:
                    electric_power = None
            else:
                electric_power = None
        else:
            electric_power = None

        if electric_power is None:
            # Modbus - value is already scaled by data_manager
            from .const import REGISTER_HEAT_PUMP_POWER

            power_data = self.coordinator.data.get(REGISTER_HEAT_PUMP_POWER, {})
            electric_power = get_register_value(power_data) or 0  # in kW
            # Convert kW to W for consistent calculation
            electric_power = electric_power * 1000

        if electric_power is not None and electric_power >= 150 and heat_power > 0:
            # Beide Leistungen in W, direkte Berechnung
            # Minimum power threshold of 150 W ensures pump is actively running
            cop = heat_power / electric_power
            return round(cop, 2)
        else:
            return None


class LastTriggeredSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """Sensor für das letzte Auslösen eines Binärsensors."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        unit,
        device_class,
        trigger_register_name,
        entity_category=None,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._trigger_register_name = trigger_register_name
        self._attr_unique_id = unique_id
        self._attr_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_translation_key = translation_key
        self._restored_value = None  # Initialize to prevent AttributeError

    async def async_added_to_hass(self):
        """Restore previous timestamp state on startup."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if (
            last_state is None
            or last_state.state is None
            or last_state.state in ("unknown", "unavailable")
        ):
            return

        restored_value = dt_util.parse_datetime(last_state.state)
        if restored_value is None:
            _LOGGER.debug(
                "Could not parse restored timestamp for %s: %s",
                self.entity_id,
                last_state.state,
            )
            return

        normal_coordinator = getattr(self.coordinator, "normal_coordinator", None)
        data_manager = getattr(normal_coordinator, "data_manager", None)
        if data_manager is not None:
            data_manager.last_triggered[self._attr_unique_id] = restored_value

        self._restored_value = restored_value
        self.coordinator.data[self._attr_unique_id] = {
            "value": restored_value,
            "input_type": "calculated",
            "register_name": self._attr_unique_id,
        }

        self.async_write_ha_state()

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._attr_unique_id)
        if data:
            value = (
                data.value
                if hasattr(data, "value")
                else data.get("value")
                if isinstance(data, dict)
                else None
            )
            if value is not None:
                self._restored_value = value
                return value
        return self._restored_value


class ExternalElectricPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor für externen elektrischen Leistungssensor."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        unit,
        device_class,
        entity_category=None,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_translation_key = translation_key

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Check if electric_power_sensor is configured
        electric_power_sensor = entry_value(self._entry, "electric_power_sensor")
        _LOGGER.debug(
            f"ExternalElectricPowerSensor available check: electric_power_sensor = {electric_power_sensor}"
        )

        if not electric_power_sensor:
            _LOGGER.debug(
                "ExternalElectricPowerSensor: Not available - no electric_power_sensor configured"
            )
            return False

        # Check if the referenced sensor exists and is available
        state = self.coordinator.hass.states.get(electric_power_sensor)
        is_available = state is not None and state.state not in [
            None,
            "unknown",
            "unavailable",
        ]
        _LOGGER.debug(
            f"ExternalElectricPowerSensor: Referenced sensor available = {is_available}"
        )
        return is_available

    @property
    def native_value(self):
        """Gibt den Wert des externen elektrischen Leistungssensors zurück."""
        electric_power_sensor = entry_value(self._entry, "electric_power_sensor")
        if electric_power_sensor:
            state = self.coordinator.hass.states.get(electric_power_sensor)
            if state and state.state not in [None, "unknown", "unavailable"]:
                try:
                    return float(state.state)
                except ValueError:
                    _LOGGER.error(
                        f"ExternalElectricPowerSensor: Cannot convert {state.state} to float"
                    )
                    return None
        return None


class DeltaTSensor(CoordinatorEntity, SensorEntity):
    """Calculated sensor for temperature difference (Delta-T)."""

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        unit,
        device_class,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key

    @property
    def native_value(self):
        """Calculate the temperature difference between flow and return."""
        from .const import (
            REGISTER_LEAVING_WATER_TEMP,
            REGISTER_RETURN_WATER_TEMP,
        )

        # Vorlauftemperatur (Leaving water temperature PHE) - already scaled
        flow_temp_data = self.coordinator.data.get(REGISTER_LEAVING_WATER_TEMP, {})
        flow_temp = get_register_value(flow_temp_data) or 0  # °C

        # Rücklauftemperatur (Return water temperature) - already scaled
        return_temp_data = self.coordinator.data.get(REGISTER_RETURN_WATER_TEMP, {})
        return_temp = get_register_value(return_temp_data) or 0  # °C

        # Delta-T berechnen und auf 2 Nachkommastellen runden
        _LOGGER.debug(f"Delta-T: {flow_temp} - {return_temp}")
        delta_t = flow_temp - return_temp
        return round(delta_t, 2)
