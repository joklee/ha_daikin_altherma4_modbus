import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..common import (
    get_register_value,
    is_entity_available,
    is_unavailable_value,
)
from ..core.const import DOMAIN, SPECIAL_REGISTER_NOT_SUPPORTED
from ..core.register_constants import (
    CALCULATED_DEVICE_INFO,
    CALCULATED_SENSORS,
    CONNECTION_SENSORS,
    INPUT_DEVICE_INFO,
    INPUT_REGISTERS,
)
from ..core.register_types import TEXT16
from ..integration.config_entry_utils import entry_value
from ..integration.repair import (
    async_create_abnormality_issue,
    async_delete_abnormality_issue,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0  # Managed by DataUpdateCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup aller Sensors über Config Entry."""
    from ..common import get_coordinator_from_entry

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
        elif calc.calc_type == "abnormality_decoded":
            entities.append(
                AbnormalityDecodedSensor(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc.register_name,
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

    # Connection diagnostic sensors on the "Enhanced" device: timestamps of
    # the last successful read/write through the shared Modbus backend.
    for conn in CONNECTION_SENSORS:
        if conn.calc_type not in ("connection_last_read", "connection_last_write"):
            continue
        entities.append(
            ConnectionTimestampSensor(
                coordinator=unified_coordinator,
                entry=entry,
                unique_id=conn.register_name,
                stamp_kind=(
                    "read" if conn.calc_type == "connection_last_read" else "write"
                ),
                device_class=conn.device_class,
                entity_category=conn.entity_category or EntityCategory.DIAGNOSTIC,
                device_info=CALCULATED_DEVICE_INFO,
                translation_key=conn.translation_key,
                disabled_by_default=conn.disabled_by_default,
            )
        )

    # Connection error counters on the "Enhanced" device: failed reads/writes
    # by category, aggregated across coordinators.
    for conn in CONNECTION_SENSORS:
        if conn.calc_type not in ("connection_read_errors", "connection_write_errors"):
            continue
        entities.append(
            ConnectionErrorSensor(
                coordinator=unified_coordinator,
                entry=entry,
                unique_id=conn.register_name,
                error_kind=(
                    "read" if conn.calc_type == "connection_read_errors" else "write"
                ),
                entity_category=conn.entity_category or EntityCategory.DIAGNOSTIC,
                device_info=CALCULATED_DEVICE_INFO,
                translation_key=conn.translation_key,
                disabled_by_default=conn.disabled_by_default,
            )
        )

    # Connection state on the "Enhanced" device: "connected"/"disconnected"
    # text sensor served live from the CoordinatorManager.
    for conn in CONNECTION_SENSORS:
        if conn.calc_type != "connection_state":
            continue
        entities.append(
            ConnectionStateSensor(
                coordinator=unified_coordinator,
                entry=entry,
                unique_id=conn.register_name,
                entity_category=conn.entity_category or EntityCategory.DIAGNOSTIC,
                device_info=CALCULATED_DEVICE_INFO,
                translation_key=conn.translation_key,
                disabled_by_default=conn.disabled_by_default,
            )
        )

    # Consecutive-failure counter on the "Enhanced" device: tracks the
    # transient/persistent outage classification (repair issue threshold).
    for conn in CONNECTION_SENSORS:
        if conn.calc_type != "connection_consecutive_failures":
            continue
        entities.append(
            ConsecutiveFailuresSensor(
                coordinator=unified_coordinator,
                entry=entry,
                unique_id=conn.register_name,
                entity_category=conn.entity_category or EntityCategory.DIAGNOSTIC,
                device_info=CALCULATED_DEVICE_INFO,
                translation_key=conn.translation_key,
                disabled_by_default=conn.disabled_by_default,
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
            # fault=1 or warning=2; report the decoded fault code (issue
            # #79, e.g. "7H-19") alongside the raw register values.
            from ..core.fault_codes import format_abnormality_label

            code_label = format_abnormality_label(code_val, sub_code_val)
            async_create_abnormality_issue(
                hass,
                entry,
                abnormality_code=code_label,
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
    from ..core.const import (
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
            from ..core.const import REGISTER_HEAT_PUMP_POWER

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
        from ..core.const import (
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


class AbnormalityDecodedSensor(CoordinatorEntity, SensorEntity):
    """Decoded abnormality fault code, e.g. "7H-19" (issue #79).

    Decodes input_22 (16-bit decimal with ASCII bytes) and combines it
    with the sub code from input_23. Reports unknown unless input_21
    signals an active fault or warning.
    """

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key

    def _fault_parts(self):
        """Return (code_raw, sub_raw) or (None, None) without active fault."""
        status = get_register_value(self.coordinator.data.get("input_21"))
        if status not in (1, 2):
            return None, None
        code_raw = get_register_value(self.coordinator.data.get("input_22"))
        sub_raw = get_register_value(self.coordinator.data.get("input_23"))
        return code_raw, sub_raw

    @property
    def available(self) -> bool:
        """Available when coordinator data is present at all."""
        return bool(self.coordinator.data)

    @property
    def native_value(self):
        """Return the decoded fault code like "7H-19", else None (unknown)."""
        from ..core.fault_codes import format_fault_code

        code_raw, sub_raw = self._fault_parts()
        if code_raw is None and sub_raw is None:
            return None
        return format_fault_code(code_raw, sub_raw)

    @property
    def extra_state_attributes(self):
        """Expose the fault meaning and raw values for automations."""
        from ..core.fault_codes import decode_fault_code, describe_fault_code

        code_raw, sub_raw = self._fault_parts()
        code = decode_fault_code(code_raw) if code_raw is not None else None
        try:
            sub = int(sub_raw) if sub_raw is not None else None
        except (TypeError, ValueError):
            sub = None
        return {
            "description": describe_fault_code(code),
            "code_raw": code_raw,
            "sub_code_raw": sub,
        }


class ConnectionTimestampSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor: last successful read/write via the Modbus backend.

    Lives on the "Enhanced" device. The value is served live from the
    CoordinatorManager (newest client timestamp across coordinators), so it
    shows `unknown` until the first successful read/write instead of a
    fabricated value.
    """

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        stamp_kind,
        device_class=None,
        entity_category=None,
        device_info=None,
        translation_key=None,
        disabled_by_default=False,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._stamp_kind = stamp_kind
        self._attr_unique_id = unique_id
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key
        self._attr_entity_registry_enabled_default = not disabled_by_default

    def _manager(self):
        """Return the CoordinatorManager behind the unified coordinator."""
        return getattr(self.coordinator, "manager", None)

    def _stamp(self):
        """Return the newest epoch timestamp for the configured kind."""
        manager = self._manager()
        if manager is None:
            return None
        if self._stamp_kind == "write":
            return manager.last_write_at
        return manager.last_read_at

    @property
    def available(self) -> bool:
        """Available once a first timestamp exists."""
        return self._stamp() is not None

    @property
    def native_value(self):
        """Return the timestamp of the last successful read/write."""
        stamp = self._stamp()
        if stamp is None:
            return None
        return dt_util.utc_from_timestamp(stamp)


class ConnectionErrorSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor: failed reads/writes via the Modbus backend.

    Lives on the "Enhanced" device. The native value is the total failure
    count for one direction; the per-category breakdown plus the newest
    failure are exposed as attributes.
    """

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        error_kind,
        entity_category=None,
        device_info=None,
        translation_key=None,
        disabled_by_default=False,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._error_kind = error_kind
        self._attr_unique_id = unique_id
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_entity_registry_enabled_default = not disabled_by_default

    def _manager(self):
        """Return the CoordinatorManager behind the unified coordinator."""
        return getattr(self.coordinator, "manager", None)

    @property
    def available(self) -> bool:
        """Available whenever the manager is reachable (zero is valid)."""
        return self._manager() is not None

    @property
    def native_value(self):
        """Return the total failure count for the configured direction."""
        manager = self._manager()
        if manager is None:
            return None
        if self._error_kind == "write":
            return manager.write_errors
        return manager.read_errors

    @property
    def extra_state_attributes(self):
        """Return the per-category breakdown and the newest failure."""
        manager = self._manager()
        if manager is None:
            return None
        last_error_at = manager.last_error_at
        return {
            **manager.error_breakdown(self._error_kind),
            "last_error": manager.last_error,
            "last_error_at": (
                dt_util.utc_from_timestamp(last_error_at).isoformat()
                if last_error_at is not None
                else None
            ),
        }


class ConnectionStateSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor: connection state as text.

    Lives on the "Enhanced" device. Reports ``connected`` while any
    coordinator holds a connected transport client, ``disconnected``
    otherwise. Stays available in both states so outages remain visible.
    """

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        entity_category=None,
        device_info=None,
        translation_key=None,
        disabled_by_default=False,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key
        self._attr_entity_registry_enabled_default = not disabled_by_default

    def _manager(self):
        """Return the CoordinatorManager behind the unified coordinator."""
        return getattr(self.coordinator, "manager", None)

    @property
    def available(self) -> bool:
        """Available whenever the manager is reachable."""
        return self._manager() is not None

    @property
    def native_value(self):
        """Return "connected" or "disconnected"."""
        manager = self._manager()
        if manager is None:
            return None
        return "connected" if manager.connection_active else "disconnected"


class ConsecutiveFailuresSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor: highest consecutive-failure count across coordinators.

    Lives on the "Enhanced" device. Counts down to a repair issue: 0 means
    healthy, higher values track the transient/persistent classification
    (see ``REPAIR_ISSUE_CONSECUTIVE_FAILURES``).
    """

    _attr_has_entity_name = True
    _attr_log_when_unavailable = False

    def __init__(
        self,
        coordinator,
        entry,
        unique_id,
        entity_category=None,
        device_info=None,
        translation_key=None,
        disabled_by_default=False,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key
        self._attr_entity_registry_enabled_default = not disabled_by_default

    def _manager(self):
        """Return the CoordinatorManager behind the unified coordinator."""
        return getattr(self.coordinator, "manager", None)

    @property
    def available(self) -> bool:
        """Available whenever the manager is reachable (zero is valid)."""
        return self._manager() is not None

    @property
    def native_value(self):
        """Return the highest consecutive-failure count."""
        manager = self._manager()
        if manager is None:
            return None
        return manager.max_consecutive_failures
