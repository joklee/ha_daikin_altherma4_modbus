from homeassistant.const import EntityCategory

DOMAIN = "ha_daikin_altherma4_modbus"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 15

DEVICE_INFO = {
    "identifiers": {("daikin_altherma_modbus", "altherma_main")},
    "name": "Daikin Altherma 4",
    "manufacturer": "Daikin",
    "model": "EPSX",
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
        "entity_category": EntityCategory.DIAGNOSTIC
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
    # Wrong data
    # {
    #     "name": "Liquid refrigerant temperature",
    #     "address": 44,
    #     "unit": "°C",
    #     "scale": 0.001,
    #     "dtype": "int16",
    #     "icon": "mdi:thermometer",
    #     "input_type": "input",
    #     "unique_id": f"{DOMAIN}_input_44",
    #     "entity_category": None
    # },

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

    # Remote / Raum
    # {
    #     "name": "Remote controller room temperature",
    #     "address": 49,
    #     "unit": "°C",
    #     "scale": 0.001,
    #     "dtype": "int16",
    #     "icon": "mdi:thermometer",
    #     "input_type": "input",
    #     "unique_id": f"{DOMAIN}_input_49",
    #     "entity_category": None
    # },

    # Leistungswerte
    {
        "name": "Heat pump power consumption",
        "address": 50,
        "unit": "W",
        "scale": 10,
        "dtype": "uint16",
        "icon": "mdi:power",
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

    # Wrong data
    # {
    #     "name": "Leaving water Add Heating setpoint lower",
    #     "address": 57,
    #     "unit": "°C",
    #     "scale": 0.001,
    #     "dtype": "int16",
    #     "icon": "mdi:thermometer",
    #     "input_type": "input",
    #     "unique_id": f"{DOMAIN}_input_57",
    #     "entity_category": None
    # },
    # {
    #     "name": "Leaving water Add Heating setpoint upper",
    #     "address": 58,
    #     "unit": "°C",
    #     "scale": 0.001,
    #     "dtype": "int16",
    #     "icon": "mdi:thermometer",
    #     "input_type": "input",
    #     "unique_id": f"{DOMAIN}_input_58",
    #     "entity_category": None
    # },
    # {
    #     "name": "Leaving water Add Cooling setpoint lower",
    #     "address": 59,
    #     "unit": "°C",
    #     "scale": 0.001,
    #     "dtype": "int16",
    #     "icon": "mdi:thermometer",
    #     "input_type": "input",
    #     "unique_id": f"{DOMAIN}_input_59",
    #     "entity_category": None
    # },
    # {
    #     "name": "Leaving water Add Cooling setpoint upper",
    #     "address": 60,
    #     "unit": "°C",
    #     "scale": 0.001,
    #     "dtype": "int16",
    #     "icon": "mdi:thermometer",
    #     "input_type": "input",
    #     "unique_id": f"{DOMAIN}_input_60",
    #     "entity_category": None
    # },

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
]

# Holding Register (beschreibbare Register)

HOLDING_REGISTERS = [
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
        "name": "Last Defrost/Restart",
        "unique_id": f"{DOMAIN}_last_defrost_restart",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 34
    },
    {
        "name": "Last Compressor Run",
        "unique_id": f"{DOMAIN}_last_compressor_run",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "entity_category": None,
        "trigger_address": 30
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
