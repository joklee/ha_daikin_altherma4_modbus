from homeassistant.const import EntityCategory

DOMAIN = "ha_daikin_altherma4_modbus"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 15

INPUT_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "input_registers")},
    "translation_key": "daikin_altherma_modbus_input_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4"
}

HOLDING_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "holding_registers")},
    "translation_key": "daikin_altherma_modbus_holding_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4"
}

CALCULATED_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "calculated_sensors")},
    "translation_key": "daikin_altherma_modbus_calculated_sensors",
    "manufacturer": "Daikin",
    "model": "Altherma 4"
}

DISCRETE_INPUT_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "discrete_input_registers")},
    "translation_key": "daikin_altherma_modbus_discrete_input_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4"
}

COIL_DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "coil_registers")},
    "translation_key": "daikin_altherma_modbus_coil_registers",
    "manufacturer": "Daikin",
    "model": "Altherma 4"
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
        "enum_map": {0: "No error", 1: "Warning", 2: "Error", 3: "Critical"},
        "translation_key": "input_20"
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
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_21"
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
        "enum_map": {32766: "No error",
        "translation_key": "22"}
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
        "enum_map": {0: "Space heating", 1: "DHW",
        "translation_key": "36"}
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
            2: "Cooling",
        "translation_key": "37"
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
        "entity_category": None,
        "translation_key": "39"
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
        "entity_category": None,
        "translation_key": "40"
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
        "entity_category": None,
        "translation_key": "41"
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
        "entity_category": None,
        "translation_key": "42"
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
        "entity_category": None,
        "translation_key": "43"
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
        "entity_category": None,
        "translation_key": "48"
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
        "entity_category": None,
        "translation_key": "50"
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
        "enum_map": {0: "Idle/Buffering", 1: "Operation",
        "translation_key": "51"}
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
        "enum_map": {0: "Idle/Buffering", 1: "Operation",
        "translation_key": "52"}
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
        "entity_category": None,
        "translation_key": "53"
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
        "entity_category": None,
        "translation_key": "54"
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
        "entity_category": None,
        "translation_key": "55"
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
        "entity_category": None,
        "translation_key": "56"
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
        "enum_map": {0: "Unsuccessful", 1: "Successful", 2: "Maintain", 3: "Heat Up",
        "translation_key": "62"}
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
        "enum_map": {0: "Free", 1: "Forced Off", 2: "Forced On", 3: "Recommended On", 4: "Reduced",
        "translation_key": "64"}
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
        "entity_category": None,
        "translation_key": "65"
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
        "entity_category": None,
        "translation_key": "66"
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
        "entity_category": None,
        "translation_key": "67"
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
        "entity_category": None,
        "translation_key": "68"
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
        "entity_category": None,
        "translation_key": "69"
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
        "entity_category": None,
        "translation_key": "70"
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
        "entity_category": None,
        "translation_key": "71"
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
        "entity_category": None,
        "translation_key": "72"
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
        "entity_category": None,
        "translation_key": "73"
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
        "entity_category": None,
        "translation_key": "74"
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
        "entity_category": None,
        "translation_key": "75"
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
        "entity_category": None,
        "translation_key": "76"
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
        "entity_category": None,
        "translation_key": "78"
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
        "enum_map": {0: "Stop", 1: "Tank Heat Up", 2: "Space heating", 3: "Space cooling", 4: "Actuator",
        "translation_key": "82"}
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
        "step": 1,
        "translation_key": "9"
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
        "step": 1,
        "translation_key": "15"
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
        "step": 1,
        "translation_key": "13"
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
        "step": 1,
        "translation_key": "53"
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
        "step": 1,
        "translation_key": "65"
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
        "step": 0.5,
        "translation_key": "57"
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
            2: "Cooling",
        "translation_key": "2"
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
            1: "ON",
        "translation_key": "3"
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
            2: "On (Manual)",
        "translation_key": "8"
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
            1: "On (Powerful)",
        "translation_key": "12"
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
            1: "On",
        "translation_key": "14"
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
            1: "Weather dependent",
        "translation_key": "67"
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
        "type": "heat_power",
        "translation_key": "pump_power_calc"
    },
    {
        "name": "Coefficient of Performance",
        "unique_id": f"{DOMAIN}_cop",
        "unit": "CoP",
        "device_class": None,
        "entity_category": None,
        "type": "cop",
        "translation_key": "cop"
    },
    {
        "name": "Delta-T",
        "unique_id": f"{DOMAIN}_delta_t",
        "unit": "°C",
        "device_class": "temperature",
        "entity_category": None,
        "type": "delta_t",
        "translation_key": "t"
    },
    {
        "name": "Last Compressor Run",
        "unique_id": f"{DOMAIN}_last_compressor_run",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 30,
        "translation_key": "compressor_run"
    },
    {
        "name": "Last Defrost",
        "unique_id": f"{DOMAIN}_last_defrost",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 16,
        "translation_key": "defrost"
    },
    {
        "name": "Last Booster Heater",
        "unique_id": f"{DOMAIN}_last_booster_heater",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 7,
        "translation_key": "booster_heater"
    },
    {
        "name": "Last DHW running",
        "unique_id": f"{DOMAIN}_last_dhw_running",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 18,
        "translation_key": "dhw_running"
    }
]

DISCRETE_INPUT_SENSORS = [
    # Status / Betriebszustände
    {
        "name": "Shut-off valve",
        "address": 0,  # 1-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_0",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_0"
    },
    {
        "name": "Backup heater relay 1",
        "address": 1,  # 2-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_1",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_1"
    },
    {
        "name": "Backup heater relay 2",
        "address": 2,  # 3-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_2",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_2"
    },
    {
        "name": "Backup heater relay 3",
        "address": 3,  # 4-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_3",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_3"
    },
    {
        "name": "Backup heater relay 4",
        "address": 4,  # 5-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_4",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_4"
    },
    {
        "name": "Backup heater relay 5",
        "address": 5,  # 6-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_5",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_5"
    },
    {
        "name": "Backup heater relay 6",
        "address": 6,  # 7-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_6",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_6"
    },
    {
        "name": "Auxiliary heating",
        "address": 7,  # 8-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_7",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_7"
    },
    {
        "name": "Storage tank",
        "address": 8,  # 9-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_8",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_8"
    },
    {
        "name": "Bivalent",
        "address": 9,  # 10-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_9",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_9"
    },
    {
        "name": "Compressor running",
        "address": 10,  # 11-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_10",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_10"
    },
    {
        "name": "Quiet mode operation active",
        "address": 11,  # 12-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_11",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_11"
    },
    {
        "name": "Holiday mode active",
        "address": 12,  # 13-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_12",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_12"
    },
    {
        "name": "Antifrost status",
        "address": 13,  # 14-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_13",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_13"
    },
    {
        "name": "Water pipe freeze prevention status",
        "address": 14,  # 15-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_14",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_14"
    },
    {
        "name": "Disinfection operation",
        "address": 15,  # 16-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_15",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_15"
    },
    {
        "name": "Defrost",
        "address": 16,  # 17-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_16",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_16"
    },
    {
        "name": "Hot start",
        "address": 17,  # 18-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_17",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_17"
    },
    {
        "name": "DHW running",
        "address": 18,  # 19-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_18",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_18"
    },
    {
        "name": "Main zone running",
        "address": 19,  # 20-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_19",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_19"
    },
    {
        "name": "Additional zone running",
        "address": 20,  # 21-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_20",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_20"
    },
    {
        "name": "Powerful tank heat up request",
        "address": 21,  # 22-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_21",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_21"
    },
    {
        "name": "Manual tank heat up request",
        "address": 22,  # 23-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_22",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_22"
    },
    {
        "name": "Emergency active",
        "address": 23,  # 24-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_23",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_23"
    },
    {
        "name": "Circulation pump running",
        "address": 24,  # 25-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_24",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_24"
    },
    {
        "name": "Imposed limit acceptance",
        "address": 25,  # 26-1
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_25",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_25"
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
        "entity_category": None,
        "translation_key": "coil_1"
    },
    {
        "name": "Main zone ON/OFF",
        "address": 1,
        "device_class": "switch",
        "input_type": "coil",
        "unique_id": f"{DOMAIN}_coil_2",
        "entity_category": None,
        "translation_key": "coil_2"
    },
    {
        "name": "Additional zone ON/OFF",
        "address": 2,
        "device_class": "switch",
        "input_type": "coil",
        "unique_id": f"{DOMAIN}_coil_3",
        "entity_category": None,
        "translation_key": "coil_3"
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
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "29"
    },
    {
        "name": "Compressor run",
        "address": 30,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_30",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "30"
    },
    {
        "name": "Booster heater run",
        "address": 31,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_31",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "31"
    },
    {
        "name": "Disinfection operation",
        "address": 32,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_32",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "32"
    },
    {
        "name": "Defrost/Restart",
        "address": 34,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_34",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "34"
    },
    {
        "name": "Hot start",
        "address": 35,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_35",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "35"
    },
    {
        "name": "Holiday mode",
        "address": 63,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_63",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "63"
    }
]
