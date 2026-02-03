import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory
from .const import (
    DOMAIN,
    INPUT_DEVICE_INFO,
    CALCULATED_DEVICE_INFO,
    INPUT_REGISTERS,
    HOLDING_REGISTERS,
    SELECT_REGISTERS,
    CALCULATED_SENSORS,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup aller Sensors über Config Entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    # Input-Register Sensoren
    for item in INPUT_REGISTERS:
        name = item["name"]
        address = item["address"]
        unit = item.get("unit", "")
        dtype = item.get("dtype", "uint16")
        scale = item.get("scale", 1)
        count = item.get("count", 1)
        icon = item.get("icon", "mdi:information")
        enum_map = item.get("enum_map")
        entity_category = item.get("entity_category")
        unique_id = item.get("unique_id", f"{DOMAIN}_input_{address}")
        translation_key = item.get("translation_key")
        
        entities.append(
            DaikinInputSensor(
                coordinator=coordinator,
                entry=entry,
                name=name,
                address=address,
                unit=unit,
                dtype=dtype,
                scale=scale,
                count=count,
                icon=icon,
                enum_map=enum_map,
                entity_category=entity_category,
                unique_id=unique_id,
                translation_key=translation_key,
                device_info=INPUT_DEVICE_INFO
            )
        )
        _LOGGER.info(f"name: {name} - translation_key {translation_key}")

    # Externer elektrischer Leistungssensor (immer erstellen, Verfügbarkeit wird über available property gesteuert)
    _LOGGER.info(f"Creating External Electric Power Sensor")
    entities.append(
        ExternalElectricPowerSensor(
            coordinator=coordinator,
            entry=entry,
            name="External Electric Power",
            unique_id=f"{DOMAIN}_external_electric_power",
            unit="W",
            device_class="power",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_info=CALCULATED_DEVICE_INFO
        )
    )

    # Berechnete Sensoren
    _LOGGER.info(f"Processing {len(CALCULATED_SENSORS)} calculated sensors")
    for calc in CALCULATED_SENSORS:
        _LOGGER.info(f"Processing calculated sensor: {calc['name']} (type: {calc['type']})")
        if calc["type"] == "heat_power":
            entities.append(
                CalculatedHeatPowerSensor(
                    coordinator=coordinator,
                    entry=entry,
                    name=calc["name"],
                    unique_id=calc["unique_id"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO
                )
            )
        elif calc["type"] == "cop":
            entities.append(
                CalculatedCoPSensor(
                    coordinator=coordinator,
                    entry=entry,
                    name=calc["name"],
                    unique_id=calc["unique_id"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO
                )
            )
        elif calc["type"] == "last_defrost_restart":
            entities.append(
                CalculatedLastDefrostRestartSensor(
                    coordinator=coordinator,
                    entry=entry,
                    name=calc["name"],
                    unique_id=calc["unique_id"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    trigger_address=calc["trigger_address"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO
                )
            )
        elif calc["type"] == "last_triggered":
            entities.append(
                LastTriggeredSensor(
                    coordinator=coordinator,
                    entry=entry,
                    name=calc["name"],
                    unique_id=calc["unique_id"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    trigger_address=calc["trigger_address"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO
                )
            )
        elif calc["type"] == "last_compressor_run":
            entities.append(
                LastTriggeredSensor(
                    coordinator=coordinator,
                    entry=entry,
                    name=calc["name"],
                    unique_id=calc["unique_id"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    trigger_address=calc["trigger_address"],
                    entity_category=calc["entity_category"],
                    device_info=CALCULATED_DEVICE_INFO
                )
            )
        elif calc["type"] == "delta_t":
            entities.append(
                DeltaTSensor(
                    coordinator=coordinator,
                    entry=entry,
                    name=calc["name"],
                    unique_id=calc["unique_id"],
                    unit=calc["unit"],
                    device_class=calc["device_class"],
                    device_info=CALCULATED_DEVICE_INFO
                )
            )

    async_add_entities(entities)


class DaikinInputSensor(CoordinatorEntity, SensorEntity):
    """A Sensor for Input-Register."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, address, unit, dtype, scale, count, icon, enum_map, entity_category=None, unique_id=None, device_info=None, translation_key=None):
        super().__init__(coordinator)
        self._entry = entry
        self._address = address
        self._dtype = dtype
        self._scale = scale
        self._count = count
        self._icon = icon
        self._enum_map = enum_map
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_device_info = device_info
        self._attr_translation_key = translation_key

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data.get(self._attr_unique_id)
        if data is None:
            return None
        val = data.get("value")
        if val is None:
            return None
        
        # Handle signed 16-bit integers
        if val > 32767:  # If value is negative (2's complement)
            val = val - 65536
            
        # ENUM Mapping
        if self._enum_map:
            val = self._enum_map.get(val, val)

        # Skalierung anwenden
        scaled_value = val * self._scale
        
        # Auf 2 Nachkommastellen runden bei °C Sensoren
        if self._attr_native_unit_of_measurement == "°C":
            return round(scaled_value, 2)
        
        return scaled_value


class CalculatedHeatPowerSensor(CoordinatorEntity, SensorEntity):
    """Berechneter Sensor für Wärmepumpenleistung."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, unique_id, unit, device_class, entity_category=None, device_info=None):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = "mdi:fire"
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        """Berechnet die Wärmeleistung in kW."""
        # Flow, Vorlauf- und Rücklauftemperatur aus den Input-Sensoren
        flow_data = self.coordinator.data.get(f"{DOMAIN}_input_48", {})
        flow_raw = flow_data.get("value", 0)  # Flow rate (roh)
        temp_vl_data = self.coordinator.data.get(f"{DOMAIN}_input_39", {})
        temp_vl_raw = temp_vl_data.get("value", 0)  # Leaving water temperature PHE (roh)
        temp_rl_data = self.coordinator.data.get(f"{DOMAIN}_input_41", {})
        temp_rl_raw = temp_rl_data.get("value", 0)  # Return water temperature (roh)

        flow = flow_raw * 0.1  # L/min
        temp_vl = temp_vl_raw # °C
        temp_rl = temp_rl_raw # °C

        delta_t = temp_vl - temp_rl
        value = flow * delta_t * 0.07  # Berechnung Wärmeleistung in kW
        return round(value, 2)


class CalculatedCoPSensor(CoordinatorEntity, SensorEntity):
    """Berechneter Sensor für Coefficient of Performance (CoP)."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, unique_id, unit, device_class, entity_category=None, device_info=None):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:gauge"
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        """Berechnet den CoP als Verhältnis von Heizleistung zu elektrischer Leistung."""
        # Heizleistung berechnen (wie in CalculatedHeatPowerSensor)
        flow_data = self.coordinator.data.get(f"{DOMAIN}_input_48", {})
        flow_raw = flow_data.get("value", 0)  # Flow rate (roh)
        temp_vl_data = self.coordinator.data.get(f"{DOMAIN}_input_39", {})
        temp_vl_raw = temp_vl_data.get("value", 0)  # Leaving water temperature PHE (roh)
        temp_rl_data = self.coordinator.data.get(f"{DOMAIN}_input_41", {})
        temp_rl_raw = temp_rl_data.get("value", 0)  # Return water temperature (roh)

        flow = flow_raw * 0.01  # L/min
        temp_vl = temp_vl_raw * 0.01  # °C
        temp_rl = temp_rl_raw * 0.01  # °C

        delta_t = temp_vl - temp_rl
        heat_power = flow * delta_t * 70  # Wärmeleistung in W
        _LOGGER.info(f"Wärmeleistung: {heat_power}")

        # Elektrische Leistung
        electric_power_sensor = self._entry.data.get("electric_power_sensor")
        _LOGGER.info(f"electric_power_sensor: {electric_power_sensor}")
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
            power_data = self.coordinator.data.get(f"{DOMAIN}_input_50", {})
            _LOGGER.info(f"power_data: {power_data}")
            electric_power_raw = power_data.get("value", 0)  # Heat pump power consumption (roh)
            electric_power = electric_power_raw * power_data.get("scale", 10);  # in W

        _LOGGER.info(f"electric_power: {electric_power}")
        if electric_power and electric_power > 0 and heat_power > 0:
            # Convert electric power from W to kW for CoP calculation
            cop = heat_power / electric_power
            _LOGGER.info(f"cop: {cop}")
            return round(cop, 2)
        else:
            _LOGGER.info(f"cop: None")
            return None


class LastTriggeredSensor(CoordinatorEntity, SensorEntity):
    """Sensor für das letzte Auslösen eines Binärsensors."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, unique_id, unit, device_class, trigger_address, entity_category=None, device_info=None):
        super().__init__(coordinator)
        self._entry = entry
        self._trigger_address = trigger_address
        self._attr_unique_id = unique_id
        self._attr_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        """Gibt den Zeitstempel des letzten Auslösens zurück."""
        return self.coordinator.data.get(f"last_triggered_{self._trigger_address}")


class ExternalElectricPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor für externen elektrischen Leistungssensor."""
    
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, unique_id, unit, device_class, entity_category=None, device_info=None):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:flash"
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO
        self._attr_entity_category = entity_category

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Check if electric_power_sensor is configured
        electric_power_sensor = self._entry.data.get("electric_power_sensor")
        _LOGGER.info(f"ExternalElectricPowerSensor available check: electric_power_sensor = {electric_power_sensor}")
        
        if not electric_power_sensor:
            _LOGGER.info("ExternalElectricPowerSensor: Not available - no electric_power_sensor configured")
            return False
        
        # Check if the referenced sensor exists and is available
        state = self.coordinator.hass.states.get(electric_power_sensor)
        is_available = state is not None and state.state not in [None, "unknown", "unavailable"]
        _LOGGER.info(f"ExternalElectricPowerSensor: Referenced sensor available = {is_available}")
        return is_available

    @property
    def native_value(self):
        """Gibt den Wert des externen elektrischen Leistungssensors zurück."""
        electric_power_sensor = self._entry.data.get("electric_power_sensor")
        if electric_power_sensor:
            state = self.coordinator.hass.states.get(electric_power_sensor)
            if state and state.state not in [None, "unknown", "unavailable"]:
                try:
                    return float(state.state)
                except ValueError:
                    _LOGGER.error(f"ExternalElectricPowerSensor: Cannot convert {state.state} to float")
                    return None
        return None


class DeltaTSensor(CoordinatorEntity, SensorEntity):
    """Calculated sensor for temperature difference (Delta-T)."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, entry, name, unique_id, unit, device_class, device_info=None):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = unique_id
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:thermometer-lines"
        self._attr_device_info = device_info or CALCULATED_DEVICE_INFO

    @property
    def native_value(self):
        """Calculate the temperature difference between flow and return."""
        # Vorlauftemperatur (Leaving water temperature PHE)
        flow_temp_data = self.coordinator.data.get(f"{DOMAIN}_input_39", {})
        flow_temp_raw = flow_temp_data.get("value", 0)
        flow_temp = flow_temp_raw * flow_temp_data.get("scale", 0.01)  # °C
        
        # Rücklauftemperatur (Return water temperature)
        return_temp_data = self.coordinator.data.get(f"{DOMAIN}_input_41", {})
        return_temp_raw = return_temp_data.get("value", 0)
        return_temp = return_temp_raw * return_temp_data.get("scale", 0.01)  # °C
        
        # Delta-T berechnen und auf 2 Nachkommastellen runden
        delta_t = flow_temp - return_temp
        return round(delta_t, 2)
