from homeassistant.const import EntityCategory

DOMAIN = "ha_daikin_altherma4_modbus"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 15

INPUT_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "input_registers")},
    "name": "Daikin Altherma 4 - Input Register",
    "manufacturer": "Daikin",
    "model": "EPSX"
}

HOLDING_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "holding_registers")},
    "name": "Daikin Altherma 4 - Holding Register",
    "manufacturer": "Daikin",
    "model": "EPSX"
}

CALCULATED_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "calculated_sensors")},
    "name": "Daikin Altherma 4 - Enhanced",
    "manufacturer": "Daikin",
    "model": "EPSX"
}

DISCRETE_INPUT_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "discrete_input_registers")},
    "name": "Daikin Altherma 4 - Discrete Input",
    "manufacturer": "Daikin",
    "model": "EPSX"
}

COIL_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "coil_registers")},
    "name": "Daikin Altherma 4 - Coil",
    "manufacturer": "Daikin",
    "model": "EPSX"
}

# Alle Input-Register aus 7.2.2 Daikin Configuration reference guide MMI user interface

INPUT_REGISTERS = [
    # Fehler / Status
    {
        "name": "Unit abnormality",
        "address": 20,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:alert-circle",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_20",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enum_map": {0: "No error", 1: "Warning", 2: "Error", 3: "Critical"}
    },
    {
        "name": "Unit abnormality code",
        "address": 21,
        "unit": None,
        "scale": 1,
        "dtype": "string",
        "count": 1,
        "icon": "mdi:alert-circle",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_21",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Unit abnormality sub code",
        "address": 22,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:alert-circle",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_22",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enum_map": {32766: "No error"}
    },

    # Status / Betriebsflags
    {
        "name": "3-way valve",
        "address": 36,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:pipe-valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_36",
        "entity_category": None,
        "enum_map": {0: "Space heating", 1: "DHW"}
    },

    # Betriebsarten
    {
        "name": "Operation mode",
        "address": 37,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:thermostat",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_37",
        "entity_category": None,
        "enum_map": {
            0: "Off",
            1: "Heating",
            2: "Cooling"
        }
    },

    # Temperaturen
    {
        "name": "Leaving water temperature PHE",
        "address": 39,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_39",
        "entity_category": None
    },
    {
        "name": "Leaving water temperature BUH",
        "address": 40,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_40",
        "entity_category": None
    },
    {
        "name": "Return water temperature",
        "address": 41,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_41",
        "entity_category": None
    },
    {
        "name": "DHW temperature",
        "address": 42,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_42",
        "entity_category": None
    },
    {
        "name": "Outside air temperature",
        "address": 43,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_43",
        "entity_category": None
    },

    # Durchfluss
    {
        "name": "Flow rate",
        "address": 48,
        "unit": "L/min",
        "scale": 0.01,
        "dtype": "uint16",
        "icon": "mdi:water-pump",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_48",
        "entity_category": None
    },

    # Leistungswerte
    {
        "name": "Heat pump power consumption",
        "address": 50,
        "unit": "W",
        "scale": 10,
        "dtype": "uint16",
        "icon": "mdi:lightning-bolt",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_50",
        "entity_category": None
    },

    # Normalbetrieb flags
    {
        "name": "DHW normal operation",
        "address": 51,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:information",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_51",
        "entity_category": None,
        "enum_map": {0: "Idle/Buffering", 1: "Operation"}
    },
    {
        "name": "Space heating/cooling normal operation",
        "address": 52,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:information",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_52",
        "entity_category": None,
        "enum_map": {0: "Idle/Buffering", 1: "Operation"}
    },

    # Sollwerte (Setpoints)
    {
        "name": "Leaving water Main Heating setpoint lower",
        "address": 53,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_53",
        "entity_category": None
    },
    {
        "name": "Leaving water Main Heating setpoint upper",
        "address": 54,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_54",
        "entity_category": None
    },
    {
        "name": "Leaving water Main Cooling setpoint lower",
        "address": 55,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_55",
        "entity_category": None
    },
    {
        "name": "Leaving water Main Cooling setpoint upper",
        "address": 56,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_56",
        "entity_category": None
    },

    # Sonstige Status / Flags
    {
        "name": "Disinfection state",
        "address": 62,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:water-pump",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_62",
        "entity_category": None,
        "enum_map": {0: "Unsuccessful", 1: "Successful", 2: "Maintain", 3: "Heat Up"}
    },
    {
        "name": "Demand response mode",
        "address": 64,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_64",
        "entity_category": None,
        "enum_map": {0: "Free", 1: "Forced Off", 2: "Forced On", 3: "Recommended On", 4: "Reduced"}
    },

    {
        "name": "Bypass valve position",
        "address": 65,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_65",
        "entity_category": None
    },
    {
        "name": "Tank valve position",
        "address": 66,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_66",
        "entity_category": None
    },
    {
        "name": "Circulation pump speed",
        "address": 67,
        "unit": "L/min",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:water-pump",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_67",
        "entity_category": None
    },
    {
        "name": "Mixed pump PWM",
        "address": 68,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:fan",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_68",
        "entity_category": None
    },
    {
        "name": "Direct pump PWM",
        "address": 69,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:fan",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_69",
        "entity_category": None
    },
    {
        "name": "Mixing valve position in mixing kit",
        "address": 70,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_70",
        "entity_category": None
    },
    {
        "name": "Mixing Leaving water temperature in mixing kit",
        "address": 71,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_71",
        "entity_category": None
    },
    {
        "name": "Space heating/cooling target for Main zone in mixing kit",
        "address": 72,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_72",
        "entity_category": None
    },
    {
        "name": "Leaving water temperature prePHE outdoor",
        "address": 73,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_73",
        "entity_category": None
    },
    {
        "name": "Leaving water temperature Tank valve",
        "address": 74,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_74",
        "entity_category": None
    },
    {
        "name": "Domestic Hot Water Upper temperature",
        "address": 75,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_75",
        "entity_category": None
    },
    {
        "name": "Domestic Hot Water Lower temperature",
        "address": 76,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_76",
        "entity_category": None
    },
    {
        "name": "Water pressure",
        "address": 78,
        "unit": "bar",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:gauge",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_78",
        "entity_category": None
    },
    {
        "name": "Unit operation mode",
        "address": 82,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_82",
        "entity_category": None,
        "enum_map": {0: "Stop", 1: "Tank Heat Up", 2: "Space heating", 3: "Space cooling", 4: "Actuator"}
    }
]

# Holding Register (beschreibbare Register)

HOLDING_REGISTERS = [
    {
        "name": "DHW reheat setpoint",
        "address": 9,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_9",
        "min_value": 30,
        "max_value": 85,
        "step": 1
    },
    {
        "name": "DHW Single heat-up setpoint (Manual)",
        "address": 15,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_15",
        "min_value": 30,
        "max_value": 85,
        "step": 1
    },
    {
        "name": "DHW boost setpoint (Powerful)",
        "address": 13,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_13",
        "min_value": 30,
        "max_value": 85,
        "step": 1
    },
    {
        "name": "Weather-dependent mode Main LWT Heating setpoint offset",
        "address": 53,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_53",
        "min_value": -5,
        "max_value": 5,
        "step": 1
    },
    {
        "name": "Weather-dependent mode Add LWT Heating setpoint offset",
        "address": 65,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_65",
        "min_value": -10,
        "max_value": 10,
        "step": 1
    },
    {
        "name": "Imposed power limit",
        "address": 57,
        "unit": "kW",
        "scale": 0.001,
        "dtype": "uint16",
        "icon": "mdi:lightning-bolt",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_57",
        "min_value": 0,
        "max_value": 20,
        "step": 0.5
    },
]

# Select Register (für Dropdown-Listen)

SELECT_REGISTERS = [
    {
        "name": "Operation mode",
        "address": 2,
        "min_v": 0,
        "max_v": 2,
        "step": 1,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_2",
        "enum_map": {
            0: "Auto",
            1: "Heating", 
            2: "Cooling"
        }
    },
    {
        "name": "Space heating/cooling",
        "address": 3,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:thermostat",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_3",
        "enum_map": {
            0: "OFF",
            1: "ON"
        }
    },
    {
        "name": "Quiet mode operation",
        "address": 8,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_8",
        "enum_map": {
            0: "Off",
            1: "On (Automatic)", 
            2: "On (Manual)"
        }
    },
    {
        "name": "DHW booster mode ON/OFF (Powerful)",
        "address": 12,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:power",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_12",
        "enum_map": {
            0: "Off",
            1: "On (Powerful)"
        }
    },
    {
        "name": "DHW Single heat-up ON/OFF (Manual)",
        "address": 14,
        "unit": None,
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:power",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_14",
        "enum_map": {
            0: "Off",
            1: "On"
        }
    },
    {
        "name": "Weather-dependent mode Heating Main",
        "address": 67,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:thermostat",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_67",
        "enum_map": {
            0: "Fixed",
            1: "Weather dependent"
        }
    },
# Holding register not readable 
    # {
    #     "name": "DHW mode setting",
    #     "address": 79,
    #     "unit": None,
    #     "scale": 1,
    #     "dtype": "int16",
    #     "icon": "mdi:water-boiler",
    #     "input_type": "holding",
    #     "unique_id": f"{DOMAIN}_holding_79",
    #     "enum_map": {
    #         0: "Reheat",
    #         1: "Schedule and reheat",
    #         2: "Scheduled",
    #         32766: "Unknown"
    #     }
    # },
]

# Berechnete Sensoren

CALCULATED_SENSORS = [
    {
        "name": "Heat Pump Power Calculated",
        "unique_id": f"{DOMAIN}_heat_pump_power_calc",
        "unit": "W",
        "device_class": "power",
        "entity_category": None,
        "type": "heat_power"
    },
    {
        "name": "Coefficient of Performance",
        "unique_id": f"{DOMAIN}_cop",
        "unit": "CoP",
        "device_class": None,
        "entity_category": None,
        "type": "cop"
    },
    {
        "name": "Delta-T",
        "unique_id": f"{DOMAIN}_delta_t",
        "unit": "°C",
        "device_class": "temperature",
        "entity_category": None,
        "type": "delta_t"
    },
    {
        "name": "Last Compressor Run",
        "unique_id": f"{DOMAIN}_last_compressor_run",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 30
    },
    {
        "name": "Last Defrost",
        "unique_id": f"{DOMAIN}_last_defrost",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 16
    },
    {
        "name": "Last Booster Heater",
        "unique_id": f"{DOMAIN}_last_booster_heater",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 7
    },
    {
        "name": "Last DHW running",
        "unique_id": f"{DOMAIN}_last_dhw_running",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 18
    }
]

DISCRETE_INPUT_SENSORS = [
    {
        "name": "Shut-off valve",
        "address": 0,  # 1-1
        "device_class": "opening",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_0",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Backup heater relay 1",
        "address": 1,  # 2-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_1",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Backup heater relay 2",
        "address": 2,  # 3-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_2",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Backup heater relay 3",
        "address": 3,  # 4-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_3",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Backup heater relay 4",
        "address": 4,  # 5-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_4",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Backup heater relay 5",
        "address": 5,  # 6-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_5",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Backup heater relay 6",
        "address": 6,  # 7-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_6",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Booster heater",
        "address": 7,  # 8-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_7",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Tank boiler",
        "address": 8,  # 9-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_8",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Bivalent",
        "address": 9,  # 10-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_9",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Compressor run",
        "address": 10,  # 11-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_10",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Quiet mode active",
        "address": 11,  # 12-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_11",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Holiday active",
        "address": 12,  # 13-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_12",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Antifrost status",
        "address": 13,  # 14-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_13",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Water pipe freeze prevention status",
        "address": 14,  # 15-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_14",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Disinfection operation",
        "address": 15,  # 16-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_15",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Defrost",
        "address": 16,  # 17-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_16",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Hot start",
        "address": 17,  # 18-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_17",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "DHW running",
        "address": 18,  # 19-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_18",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Main zone running",
        "address": 19,  # 20-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_19",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Additional zone running",
        "address": 20,  # 21-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_20",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Powerful tank heat up request",
        "address": 21,  # 22-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_21",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Manual tank heat up request",
        "address": 22,  # 23-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_22",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Emergency active",
        "address": 23,  # 24-1
        "device_class": "problem",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_23",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Circulation pump running",
        "address": 24,  # 25-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_24",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Imposed limit acceptance",
        "address": 25,  # 26-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_25",
        "entity_category": EntityCategory.DIAGNOSTIC
    }
]

# Alle Coil-Register aus 7.2.4 Daikin Configuration reference guide

COIL_SENSORS = [
    {
        "name": "Domestic Hot Water ON/OFF",
        "address": 0,
        "device_class": "switch",
        "input_type": "coil",
        "unique_id": f"{DOMAIN}_coil_1",
        "entity_category": None
    },
    {
        "name": "Main zone ON/OFF",
        "address": 1,
        "device_class": "switch",
        "input_type": "coil",
        "unique_id": f"{DOMAIN}_coil_2",
        "entity_category": None
    },
    {
        "name": "Additional zone ON/OFF",
        "address": 2,
        "device_class": "switch",
        "input_type": "coil",
        "unique_id": f"{DOMAIN}_coil_3",
        "entity_category": None
    }
]

# Diagnose Sensoren

BINARY_SENSORS = [
    {
        "name": "Circulation pump running",
        "address": 29,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_29",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Compressor run",
        "address": 30,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_30",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Booster heater run",
        "address": 31,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_31",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Disinfection operation",
        "address": 32,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_32",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Defrost/Restart",
        "address": 34,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_34",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Hot start",
        "address": 35,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_35",
        "entity_category": EntityCategory.DIAGNOSTIC
    },
    {
        "name": "Holiday mode",
        "address": 63,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_63",
        "entity_category": EntityCategory.DIAGNOSTIC
    }
]
