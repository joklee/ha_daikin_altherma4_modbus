from homeassistant.const import EntityCategory

DOMAIN = "ha_daikin_altherma4_modbus"
ENTITY_PREFIX = "altherma4_";
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
        "address": 21,
        "unit": None,
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:alert-circle",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_21",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enum_map": {0: "Kein Fehler", 1: "Störung", 2: "Warnung"},
        "translation_key": "input_21"
    },
    {
        "name": "Unit abnormality code",
        "address": 22,
        "unit": None,
        "scale": 1,
        "dtype": "string",
        "count": 1,
        "icon": "mdi:alert-circle",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_22",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_22"
    },
    {
        "name": "Unit abnormality sub code",
        "address": 23,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:alert-circle",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_23",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enum_map": {32766: "No error"},
        "translation_key": "input_23"
    },

    # Status / Betriebsflags
    {
        "name": "3-way valve",
        "address": 37,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:pipe-valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_37",
        "entity_category": None,
        "enum_map": {0: "Space heating", 1: "DHW"},
        "translation_key": "input_37"
    },

    # Betriebsarten
    {
        "name": "Operation mode",
        "address": 38,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:thermostat",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_38",
        "entity_category": None,
        "enum_map": {
            0: "Off",
            1: "Heating",
            2: "Cooling",
        "translation_key": "input_38"
        }
    },

    # Temperaturen
    {
        "name": "Leaving water temperature PHE",
        "address": 40,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_40",
        "entity_category": None,
        "translation_key": "input_40"
    },
    {
        "name": "Leaving water temperature BUH",
        "address": 41,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_41",
        "entity_category": None,
        "translation_key": "input_41"
    },
    {
        "name": "Return water temperature",
        "address": 42,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_42",
        "entity_category": None,
        "translation_key": "input_42"
    },
    {
        "name": "DHW temperature",
        "address": 43,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_43",
        "entity_category": None,
        "translation_key": "input_43"
    },
    {
        "name": "Outside air temperature",
        "address": 44,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_44",
        "entity_category": None,
        "translation_key": "input_44"
    },

    # Durchfluss
    {
        "name": "Flow rate",
        "address": 49,
        "unit": "L/min",
        "scale": 0.01,
        "dtype": "uint16",
        "icon": "mdi:water-pump",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_49",
        "entity_category": None,
        "translation_key": "input_49"
    },

    # Leistungswerte
    {
        "name": "Heat pump power consumption",
        "address": 51,
        "unit": "W",
        "scale": 10,
        "dtype": "uint16",
        "icon": "mdi:lightning-bolt",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_51",
        "entity_category": None,
        "translation_key": "input_51"
    },

    # Normalbetrieb flags
    {
        "name": "DHW normal operation",
        "address": 52,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:information",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_52",
        "entity_category": None,
        "enum_map": {0: "Idle/Buffering", 1: "Operation",
        "translation_key": "input_52"}
    },
    {
        "name": "Space heating/cooling normal operation",
        "address": 53,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:information",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_53",
        "entity_category": None,
        "enum_map": {0: "Idle/Buffering", 1: "Operation",
        "translation_key": "input_53"}
    },

    # Sollwerte (Setpoints)
    {
        "name": "Leaving water Main Heating setpoint lower",
        "address": 54,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_54",
        "entity_category": None,
        "translation_key": "input_54"
    },
    {
        "name": "Leaving water Main Heating setpoint upper",
        "address": 55,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_55",
        "entity_category": None,
        "translation_key": "input_55"
    },
    {
        "name": "Leaving water Main Cooling setpoint lower",
        "address": 56,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_56",
        "entity_category": None,
        "translation_key": "input_56"
    },
    {
        "name": "Leaving water Main Cooling setpoint upper",
        "address": 57,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_57",
        "entity_category": None,
        "translation_key": "input_57"
    },

    # Zusätzliche Sollwert-Grenzen
    {
        "name": "Leaving water Add Heating setpoint lower",
        "address": 58,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_58",
        "entity_category": None,
        "translation_key": "input_58"
    },
    {
        "name": "Leaving water Add Heating setpoint upper",
        "address": 59,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_59",
        "entity_category": None,
        "translation_key": "input_59"
    },
    {
        "name": "Leaving water Add Cooling setpoint lower",
        "address": 60,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_60",
        "entity_category": None,
        "translation_key": "input_60"
    },
    {
        "name": "Leaving water Add Cooling setpoint upper",
        "address": 61,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_61",
        "entity_category": None,
        "translation_key": "input_61"
    },

    # Sonstige Status / Flags
    {
        "name": "Disinfection state",
        "address": 63,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:water-pump",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_63",
        "entity_category": None,
        "enum_map": {0: "Unsuccessful", 1: "Successful", 2: "Maintain", 3: "Heat Up"},
        "translation_key": "input_63"
    },
    {
        "name": "Holiday mode",
        "address": 64,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:beach",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_64",
        "entity_category": None,
        "enum_map": {0: "OFF", 1: "ON"},
        "translation_key": "input_64"
    },
    {
        "name": "Demand response mode",
        "address": 65,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:lightning-bolt",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_65",
        "entity_category": None,
        "enum_map": {0: "Free", 1: "Forced Off", 2: "Forced On", 3: "Recommended On", 4: "Reduced"},
        "translation_key": "input_65"
    },

    {
        "name": "Bypass valve position",
        "address": 66,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_66",
        "entity_category": None,
        "translation_key": "input_66"
    },
    {
        "name": "Tank valve position",
        "address": 67,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_67",
        "entity_category": None,
        "translation_key": "input_67"
    },
    {
        "name": "Circulation pump speed",
        "address": 68,
        "unit": "L/min",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:water-pump",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_68",
        "entity_category": None,
        "translation_key": "input_68"
    },
    {
        "name": "Mixed pump PWM",
        "address": 69,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:fan",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_69",
        "entity_category": None,
        "translation_key": "input_69"
    },
    {
        "name": "Direct pump PWM",
        "address":70,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:fan",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_70",
        "entity_category": None,
        "translation_key": "input_70"
    },
    {
        "name": "Mixing valve position in mixing kit",
        "address": 71,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_71",
        "entity_category": None,
        "translation_key": "input_71"
    },
    {
        "name": "Mixing Leaving water temperature in mixing kit",
        "address": 72,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_72",
        "entity_category": None,
        "translation_key": "input_72"
    },
    {
        "name": "Space heating/cooling target for Main zone in mixing kit",
        "address": 73,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_73",
        "entity_category": None,
        "translation_key": "input_73"
    },
    {
        "name": "Leaving water temperature prePHE outdoor",
        "address": 74,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_74",
        "entity_category": None,
        "translation_key": "input_74"
    },
    {
        "name": "Leaving water temperature Tank valve",
        "address": 75,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_75",
        "entity_category": None,
        "translation_key": "input_75"
    },
    {
        "name": "Domestic Hot Water Upper temperature",
        "address": 76,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_76",
        "entity_category": None,
        "translation_key": "input_76"
    },
    {
        "name": "Domestic Hot Water Lower temperature",
        "address": 77,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_77",
        "entity_category": None,
        "translation_key": "input_77"
    },
    {
        "name": "Water pressure",
        "address": 79,
        "unit": "bar",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:gauge",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_79",
        "entity_category": None,
        "translation_key": "input_79"
    },
    {
        "name": "Unit operation mode",
        "address": 83,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_83",
        "entity_category": None,
        "enum_map": {0: "Stop", 1: "Tank Heat Up", 2: "Space heating", 3: "Space cooling", 4: "Actuator",
        "translation_key": "input_83"}
    }
]

# Holding Register (beschreibbare Register)

HOLDING_REGISTERS = [
    {
        "name": "Main Heating Setpoint",
        "address": 1,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_1",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "translation_key": "input_1"
    },
    {
        "name": "Main Cooling Setpoint",
        "address": 2,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_2",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "translation_key": "input_2"
    },
    {
        "name": "Room Thermostat Heating Setpoint Main",
        "address": 6,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_6",
        "min_value": 12,
        "max_value": 30,
        "step": 1,
        "translation_key": "input_6"
    },
    {
        "name": "Room Thermostat Cooling Setpoint Main",
        "address": 7,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_7",
        "min_value": 12,
        "max_value": 35,
        "step": 1,
        "translation_key": "input_7"
    },
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
        "translation_key": "input_9"
    },
    {
        "name": "Weather-dependent mode Heating Main",
        "address": 68,
        "min_v": 0,
        "max_v": 1,
        "step": 1,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_68",
        "enum_map": {
            0: "Constant",
            1: "Weather-dependent",
        "translation_key": "input_68"
        }
    },
    {
        "name": "Weather-dependent mode Cooling Main",
        "address": 69,
        "min_v": 0,
        "max_v": 1,
        "step": 1,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_69",
        "enum_map": {
            0: "Constant",
            1: "Weather-dependent",
        "translation_key": "input_69"
        }
    },
    {
        "name": "Thermostat Request Main",
        "address": 74,
        "min_v": 0,
        "max_v": 2,
        "step": 1,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:thermostat",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_74",
        "enum_map": {
            0: "None",
            1: "Heating",
            2: "Cooling",
        "translation_key": "input_74"
        }
    },
    {
        "name": "Thermostat Request Additional",
        "address": 75,
        "min_v": 0,
        "max_v": 2,
        "step": 1,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:thermostat",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_75",
        "enum_map": {
            0: "None",
            1: "Heating",
            2: "Cooling",
        "translation_key": "input_75"
        }
    },
    # {
    #     "name": "DHW Mode Setting",
    #     "address": 80,
    #     "min_v": 0,
    #     "max_v": 2,
    #     "step": 1,
    #     "unit": None,
    #     "scale": 1,
    #     "dtype": "uint16",
    #     "icon": "mdi:cog",
    #     "input_type": "holding",
    #     "unique_id": f"{DOMAIN}_holding_80",
    #     "enum_map": {
    #         0: "Keep Warm",
    #         1: "Program and Keep Warm",
    #         2: "Scheduled",
    #     "translation_key": "input_80"
    #     }
    # },
    {
        "name": "DHW Keep Warm Setpoint",
        "address": 10,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_10",
        "min_value": 30,
        "max_value": 85,
        "step": 1,
        "translation_key": "input_10"
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
        "translation_key": "input_13"
    },
    {
        "name": "DHW Powerful Additional Setpoint",
        "address": 14,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_14",
        "min_value": 30,
        "max_value": 85,
        "step": 1,
        "translation_key": "input_14"
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
        "translation_key": "input_15"
    },
    {
        "name": "DHW Single Heat-up Setpoint (Manual)",
        "address": 16,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_16",
        "min_value": 30,
        "max_value": 85,
        "step": 1,
        "translation_key": "input_16"
    },
    {
        "name": "Smart Grid Operation Mode",
        "address": 56,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_56",
        "min_value": 0,
        "max_value": 3,
        "step": 1,
        "translation_key": "input_56"
    },
    {
        "name": "Weather-dependent mode Main LWT Heating setpoint offset",
        "address": 54,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_54",
        "min_value": -5,
        "max_value": 5,
        "step": 1,
        "translation_key": "input_54"
    },
    {
        "name": "Weather-dependent mode Add LWT Heating setpoint offset",
        "address": 55,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_55",
        "min_value": -10,
        "max_value": 10,
        "step": 1,
        "translation_key": "input_55"
    },
    {
        "name": "Imposed power limit",
        "address": 58,
        "unit": "kW",
        "scale": 0.001,
        "dtype": "uint16",
        "icon": "mdi:lightning-bolt",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_58",
        "min_value": 0,
        "max_value": 20,
        "step": 0.5,
        "translation_key": "input_58"
    },
    {
        "name": "Additional Heating Setpoint",
        "address": 63,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_63",
        "min_value": 3,
        "max_value": 85,
        "step": 1,
        "translation_key": "input_63"
    },
    {
        "name": "Additional Cooling Setpoint",
        "address": 64,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_64",
        "min_value": 3,
        "max_value": 85,
        "step": 1,
        "translation_key": "input_64"
    },
    {
        "name": "Weather-dependent mode Add VLT Heating offset",
        "address": 66,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_66",
        "min_value": -10,
        "max_value": 10,
        "step": 1,
        "translation_key": "input_66"
    },
    {
        "name": "Weather-dependent mode Add VLT Cooling offset",
        "address": 67,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_67",
        "min_value": -10,
        "max_value": 10,
        "step": 1,
        "translation_key": "input_67"
    },
    {
        "name": "Room Thermostat Heating Setpoint Main",
        "address": 76,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_76",
        "min_value": 12,
        "max_value": 30,
        "step": 1,
        "translation_key": "input_76"
    },
    {
        "name": "Room Thermostat Cooling Setpoint Main",
        "address": 77,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_77",
        "min_value": 12,
        "max_value": 35,
        "step": 1,
        "translation_key": "input_77"
    },
    {
        "name": "Room Thermostat Heating Setpoint Additional",
        "address": 78,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_78",
        "min_value": 12,
        "max_value": 30,
        "step": 1,
        "translation_key": "input_78"
    },
    {
        "name": "Room Thermostat Cooling Setpoint Additional",
        "address": 79,
        "unit": "°C",
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:thermometer",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_79",
        "min_value": 12,
        "max_value": 35,
        "step": 1,
        "translation_key": "input_79"
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
        "translation_key": "holding_2",
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
        "translation_key": "holding_3",
        "enum_map": {
            0: "OFF",
            1: "ON"
        }
    },
    {
        "name": "Quiet mode operation",
        "address": 9,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_9",
        "translation_key": "holding_9",
        "enum_map": {
            0: "Off",
            1: "On (Automatic)", 
            2: "On (Manual)"
        }
    },
    {
        "name": "DHW booster mode ON/OFF (Powerful)",
        "address": 13,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:power",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_13",
        "translation_key": "holding_13",
        "enum_map": {
            0: "Off",
            1: "On (Powerful)"
        }
    },
    {
        "name": "DHW Single heat-up ON/OFF (Manual)",
        "address": 15,
        "unit": None,
        "scale": 1,
        "dtype": "int16",
        "icon": "mdi:power",
        "input_type": "holding",
        "unique_id": f"{DOMAIN}_holding_15",
        "translation_key": "holding_15",
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
        "translation_key": "holding_67",
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
        "translation_key": "delta_t"
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
        "address": 1,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_0",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_0"
    },
    {
        "name": "Backup heater relay 1",
        "address": 2,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_1",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_1"
    },
    {
        "name": "Backup heater relay 2",
        "address": 3,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_2",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_2"
    },
    {
        "name": "Backup heater relay 3",
        "address": 4,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_3",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_3"
    },
    {
        "name": "Backup heater relay 4",
        "address": 5,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_4",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_4"
    },
    {
        "name": "Backup heater relay 5",
        "address": 6,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_5",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_5"
    },
    {
        "name": "Backup heater relay 6",
        "address": 7,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_6",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_6"
    },
    {
        "name": "Auxiliary heating",
        "address": 8,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_7",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_7"
    },
    {
        "name": "Storage tank",
        "address": 9,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_8",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_8"
    },
    {
        "name": "Bivalent",
        "address": 10,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_9",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_9"
    },
    {
        "name": "Compressor running",
        "address": 11,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_10",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_10"
    },
    {
        "name": "Quiet mode operation active",
        "address": 12,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_11",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_11"
    },
    {
        "name": "Holiday mode active",
        "address": 13,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_12",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_12"
    },
    {
        "name": "Antifrost status",
        "address": 14,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_13",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_13"
    },
    {
        "name": "Water pipe freeze prevention status",
        "address": 15,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_14",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_14"
    },
    {
        "name": "Disinfection operation",
        "address": 16,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_15",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_15"
    },
    {
        "name": "Defrost",
        "address": 17,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_16",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_16"
    },
    {
        "name": "Hot start",
        "address": 18,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_17",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_17"
    },
    {
        "name": "DHW running",
        "address": 19,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_18",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_18"
    },
    {
        "name": "Main zone running",
        "address": 20,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_19",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_19"
    },
    {
        "name": "Additional zone running",
        "address": 21,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_20",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_20"
    },
    {
        "name": "Powerful tank heat up request",
        "address": 22,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_21",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_21"
    },
    {
        "name": "Manual tank heat up request",
        "address": 23,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_22",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_22"
    },
    {
        "name": "Emergency active",
        "address": 24,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_23",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_23"
    },
    {
        "name": "Circulation pump running",
        "address": 25,
        "device_class": "running",
        "input_type": "discrete_input",
        "unique_id": f"{DOMAIN}_discrete_24",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "discrete_24"
    },
    {
        "name": "Imposed limit acceptance",
        "address": 26,
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
        "address": 1,
        "device_class": "switch",
        "input_type": "coil",
        "unique_id": f"{DOMAIN}_coil_1",
        "entity_category": None,
        "translation_key": "coil_1"
    },
    {
        "name": "Main zone ON/OFF",
        "address": 2,
        "device_class": "switch",
        "input_type": "coil",
        "unique_id": f"{DOMAIN}_coil_2",
        "entity_category": None,
        "translation_key": "coil_2"
    },
    {
        "name": "Additional zone ON/OFF",
        "address": 3,
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
        "translation_key": "input_29"
    },
    {
        "name": "Compressor run",
        "address": 30,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_30",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_30"
    },
    {
        "name": "Booster heater run",
        "address": 31,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_31",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_31"
    },
    {
        "name": "Disinfection operation",
        "address": 32,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_32",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_32"
    },
    {
        "name": "Defrost/Restart",
        "address": 34,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_34",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_34"
    },
    {
        "name": "Hot start",
        "address": 35,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_35",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_35"
    },
    {
        "name": "Holiday mode",
        "address": 63,
        "device_class": "running",
        "input_type": "input",
        "unique_id": f"{DOMAIN}_input_63",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "translation_key": "input_63"
    }
]
