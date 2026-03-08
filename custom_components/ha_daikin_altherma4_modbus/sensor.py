import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import (
    DOMAIN,
    INPUT_DEVICE_INFO,
    CALCULATED_DEVICE_INFO,
    INPUT_REGISTERS,
    CALCULATED_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


def _entry_value(entry, key, default=None):
    """Read config from options first, then fallback to data."""
    options = getattr(entry, "options", {}) or {}
    data = getattr(entry, "data", {}) or {}
    return options.get(key, data.get(key, default))


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup aller Sensors über Config Entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    unified_coordinator = coordinators.get("coordinator")
    coordinators.get("normal_coordinator")
    coordinators.get("slow_coordinator")

    if unified_coordinator is None:
        _LOGGER.error("Unified coordinator not found in hass data")
        return
    entities = []

    # Input-Register Sensoren (nur ohne device_class running/problem)
    for item in INPUT_REGISTERS:
        device_class = item.get("device_class")
        if device_class in ["running", "problem"]:
            continue  # Nur als Binärsensoren erstellen

        address = item["address"]
        register_name = item.get("register_name")
        unit = item.get("unit", "")
        dtype = item.get("dtype", "uint16")
        scale = item.get("scale", 1)
        count = item.get("count", 1)
        icon = item.get("icon", "mdi:information")
        enum_map = item.get("enum_map")
        entity_category = item.get("entity_category")
        unique_id = item.get("unique_id") or f"{DOMAIN}_{register_name}"
        translation_key = item.get("translation_key")

        entities.append(
            DaikinInputSensor(
                coordinator=unified_coordinator,
                entry=entry,
                address=address,
                unit=unit,
                dtype=dtype,
                scale=scale,
                count=count,
                icon=icon,
                enum_map=enum_map,
                entity_category=entity_category,
                register_name=register_name,
                unique_id=unique_id,
                translation_key=translation_key,
                device_info=INPUT_DEVICE_INFO,
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
            f"Processing calculated sensor: {calc['name']} (type: {calc['type']})"
        )
        if calc["type"] == "heat_power":
            entities.append(
                ThermalHeatOutput(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc["register_name"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.get("translation_key"),
                )
            )
        elif calc["type"] == "cop":
            entities.append(
                CalculatedCoPSensor(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc["register_name"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.get("translation_key"),
                )
            )
        elif calc["type"] == "last_triggered":
            entities.append(
                LastTriggeredSensor(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc["register_name"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    trigger_register_name=calc["trigger_register_name"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.get("translation_key"),
                )
            )
        elif calc["type"] == "delta_t":
            entities.append(
                DeltaTSensor(
                    coordinator=unified_coordinator,
                    entry=entry,
                    unique_id=calc["register_name"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    device_info=CALCULATED_DEVICE_INFO,
                    translation_key=calc.get("translation_key"),
                )
            )

    async_add_entities(entities)


class DaikinInputSensor(CoordinatorEntity, SensorEntity):
    """A Sensor for Input-Register."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry,
        address,
        unit,
        dtype,
        scale,
        count,
        icon,
        enum_map,
        register_name,
        entity_category=None,
        unique_id=None,
        device_info=None,
        translation_key=None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._dtype = dtype
        self._scale = scale
        self._count = count
        self._icon = icon
        self._enum_map = enum_map
        self._attr_register_name = register_name
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key
        self._attr_icon = icon

        # Set device_class to 'enum' for sensors with enum_map
        if enum_map:
            self._attr_device_class = "enum"
            # Set options to the possible enum values
            self._attr_options = list(enum_map.values())

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        data = self.coordinator.data.get(self._attr_register_name)
        if data is None:
            return False

        val = data.get("value")
        if val is None:
            return False

        # Convert to integer if it's a string
        try:
            val = int(val)
        except (ValueError, TypeError):
            return False

        # Sensor is unavailable if value is 32765 or 32766
        if val == 32765 or val == 32766:
            return False

        return True

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data.get(self._attr_register_name)
        if data is None:
            return None
        val = data.get("value")
        if val is None:
            return None

        # Handle string data types directly
        if self._dtype == "string":
            return str(val) if val is not None else None

        # Check if value is already scaled by checking if scale is stored in data
        data_scale = data.get("scale")

        # Convert to appropriate type based on sensor characteristics
        try:
            # For scaled sensors, keep as float to preserve decimal places
            if self._scale != 1 or (data_scale is not None and data_scale != 1):
                # This is a scaled sensor - convert to float
                val = float(val)
            else:
                # This is not a scaled sensor - convert to int
                val = int(val)
        except (ValueError, TypeError):
            return None

        # Return None for unavailable value (32765 or 32766)
        if val == 32765 or val == 32766:
            return None

        # Handle signed 16-bit integers
        if val > 32767:  # If value is negative (2's complement)
            val = val - 65536

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

        if data_scale is not None:
            # Value is already scaled by data_manager
            scaled_value = val
        else:
            # Value is not scaled yet, apply scaling
            scaled_value = val * self._scale

        # Auf 2 Nachkommastellen runden bei °C Sensoren
        if self._attr_native_unit_of_measurement == "°C":
            final_value = round(scaled_value, 2)
            return final_value

        return scaled_value


def calculate_thermal_heat_output(coordinator):
    """Berechnet die thermische Leistung in W."""
    # Flow, Vorlauf- und Rücklauftemperatur aus den Input-Sensoren
    flow_data = coordinator.data.get("input_49", {})
    flow_raw = flow_data.get("value", 0)  # Flow rate (roh)
    temp_vl_data = coordinator.data.get("input_40", {})
    temp_vl_raw = temp_vl_data.get("value", 0)  # Leaving water temperature PHE (roh)
    temp_rl_data = coordinator.data.get("input_42", {})
    temp_rl_raw = temp_rl_data.get("value", 0)  # Return water temperature (roh)

    # Check if values are already scaled by checking if scale is stored in data
    flow_scale = flow_data.get("scale")
    if flow_scale is not None:
        flow = flow_raw  # Already scaled by data_manager
    else:
        flow = flow_raw * 0.01  # L/min (korrekte Skalierung)

    temp_vl_scale = temp_vl_data.get("scale")
    if temp_vl_scale is not None:
        temp_vl = temp_vl_raw  # Already scaled by data_manager
    else:
        temp_vl = temp_vl_raw * 0.01  # °C (korrekte Skalierung)

    temp_rl_scale = temp_rl_data.get("scale")
    if temp_rl_scale is not None:
        temp_rl = temp_rl_raw  # Already scaled by data_manager
    else:
        temp_rl = temp_rl_raw * 0.01  # °C (korrekte Skalierung)

    delta_t = temp_vl - temp_rl
    thermal_heat_output = flow * delta_t * 70  # Berechnung thermische Leistung in W
    _LOGGER.debug(f"flow: {flow} L/min")
    _LOGGER.debug(f"delta_t: {delta_t} K")
    _LOGGER.debug(f"thermal_heat_output: {thermal_heat_output} W")
    return round(thermal_heat_output, 2)


class ThermalHeatOutput(CoordinatorEntity, SensorEntity):
    """Berechneter Sensor für Wärmepumpenleistung."""

    _attr_has_entity_name = True

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
        self._attr_icon = "mdi:fire"
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_translation_key = translation_key
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
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:gauge"
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
        electric_power_sensor = _entry_value(self._entry, "electric_power_sensor")
        if electric_power_sensor:
            # Externer Sensor
            state = self.coordinator.hass.states.get(electric_power_sensor)
            if state and state.state not in [None, "unknown", "unavailable"]:
                try:
                    electric_power = float(state.state)
                except ValueError:
                    electric_power = None
            else:
                electric_power = None
        else:
            electric_power = None

        if electric_power is None:
            # Modbus
            power_data = self.coordinator.data.get("input_51", {})
            electric_power_raw = power_data.get(
                "value", 0
            )  # Heat pump power consumption (roh)

            # Check if value is already scaled by checking if scale is stored in data
            data_scale = power_data.get("scale")

            if data_scale is not None:
                # Value is already scaled by data_manager
                electric_power = electric_power_raw
            else:
                # Value is not scaled yet, apply scaling
                electric_power = electric_power_raw * power_data.get(
                    "scale", 10
                )  # in W

        if electric_power and electric_power > 0 and heat_power > 0:
            # Beide Leistungen in W, direkte Berechnung
            cop = heat_power / electric_power
            return round(cop, 2)
        else:
            return None


class LastTriggeredSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """Sensor für das letzte Auslösen eines Binärsensors."""

    _attr_has_entity_name = True

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
        if data and isinstance(data, dict):
            value = data.get("value")
            if value is not None:
                self._restored_value = value
                return value
        return self._restored_value


class ExternalElectricPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor für externen elektrischen Leistungssensor."""

    _attr_has_entity_name = True

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
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:flash"
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category
        self._attr_translation_key = translation_key

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Check if electric_power_sensor is configured
        electric_power_sensor = _entry_value(self._entry, "electric_power_sensor")
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
        electric_power_sensor = _entry_value(self._entry, "electric_power_sensor")
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
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:thermometer-lines"
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_translation_key = translation_key

    @property
    def native_value(self):
        """Calculate the temperature difference between flow and return."""
        # Vorlauftemperatur (Leaving water temperature PHE)
        flow_temp_data = self.coordinator.data.get("input_40", {})
        flow_temp = flow_temp_data.get("value", 0)

        # Rücklauftemperatur (Return water temperature)
        return_temp_data = self.coordinator.data.get("input_42", {})
        return_temp = return_temp_data.get("value", 0)

        # Delta-T berechnen und auf 2 Nachkommastellen runden
        delta_t = flow_temp - return_temp
        return round(delta_t, 2)
