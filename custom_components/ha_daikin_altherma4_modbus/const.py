DOMAIN = "ha_daikin_altherma4_modbus"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 15
UNIQUE_ID_PREFIX = "altherma4_modbus_"

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
        "name": "Unit error",
        "address": 20,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:alert-circle",
        "entity_category": "diagnostic",
        "enum_map": {0: "No error", 1: "Warning", 2: "Error", 3: "Critical"}
    },
    {
        "name": "Unit error code",
        "address": 21,
        "unit": None,
        "scale": 1,
        "dtype": "string",
        "count": 1,
        "icon": "mdi:alert-circle",
        "entity_category": "diagnostic"
    },
    {
        "name": "Unit error sub code",
        "address": 22,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:alert-circle",
        "entity_category": "diagnostic"
    },

    # Status / Betriebsflags
    {
        "name": "3-way valve",
        "address": 36,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:pipe-valve",
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
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water temperature BUH",
        "address": 40,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Return water temperature",
        "address": 41,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "DHW temperature",
        "address": 42,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Outside air temperature",
        "address": 43,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Liquid refrigerant temperature",
        "address": 44,
        "unit": "°C",
        "scale": 0.001,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },

    # Durchfluss
    {
        "name": "Flow rate",
        "address": 48,
        "unit": "L/min",
        "scale": 0.01,
        "dtype": "uint16",
        "icon": "mdi:water-pump"
    },

    # Remote / Raum
    {
        "name": "Remote controller room temperature",
        "address": 49,
        "unit": "°C",
        "scale": 0.001,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },

    # Leistungswerte
    {
        "name": "Heat pump power consumption",
        "address": 50,
        "unit": "kW",
        "scale": 0.01,
        "dtype": "uint16",
        "icon": "mdi:power"
    },

    # Normalbetrieb flags
    {
        "name": "DHW normal operation",
        "address": 51,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:information",
        "enum_map": {0: "Idle/Buffering", 1: "Operation"}
    },
    {
        "name": "Space heating/cooling normal operation",
        "address": 52,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:information",
        "enum_map": {0: "Idle/Buffering", 1: "Operation"}
    },

    # Sollwerte (Setpoints)
    {
        "name": "Leaving water Main Heating setpoint lower",
        "address": 53,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water Main Heating setpoint upper",
        "address": 54,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water Main Cooling setpoint lower",
        "address": 55,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water Main Cooling setpoint upper",
        "address": 56,
        "unit": "°C",
        "scale": 0.01,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water Add Heating setpoint lower",
        "address": 57,
        "unit": "°C",
        "scale": 0.001,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water Add Heating setpoint upper",
        "address": 58,
        "unit": "°C",
        "scale": 0.001,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water Add Cooling setpoint lower",
        "address": 59,
        "unit": "°C",
        "scale": 0.001,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },
    {
        "name": "Leaving water Add Cooling setpoint upper",
        "address": 60,
        "unit": "°C",
        "scale": 0.001,
        "dtype": "int16",
        "icon": "mdi:thermometer"
    },

    # Sonstige Status / Flags
    {
        "name": "Disinfection state",
        "address": 62,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:water-pump",
        "enum_map": {0: "Unsuccessful", 1: "Successful", 2: "Maintain", 3: "Heat Up"}
    },
    {
        "name": "Demand response mode",
        "address": 64,
        "unit": None,
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:cog",
        "enum_map": {0: "Free", 1: "Forced Off", 2: "Forced On", 3: "Recommended On", 4: "Reduced"}
    },

    {
        "name": "Bypass valve position",
        "address": 65,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve"
    },
    {
        "name": "Tank valve position",
        "address": 66,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve"
    },
    {
        "name": "Circulation pump speed",
        "address": 67,
        "unit": "L/min",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:water-pump"
    },
    {
        "name": "Mixed pump PWM",
        "address": 68,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:fan"
    },
    {
        "name": "Direct pump PWM",
        "address": 69,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:fan"
    },
    {
        "name": "Mixing valve position in mixing kit",
        "address": 70,
        "unit": "%",
        "scale": 1,
        "dtype": "uint16",
        "icon": "mdi:valve"
    },
]

# Berechnete Sensoren

CALCULATED_SENSORS = [
    {
        "name": "Heat Pump Power Calculated",
        "unique_id": f"{UNIQUE_ID_PREFIX}heat_pump_power_calc",
        "unit": "W",
        "device_class": "power",
        "type": "heat_power"
    },
    {
        "name": "Coefficient of Performance",
        "unique_id": f"{UNIQUE_ID_PREFIX}cop",
        "unit": "CoP",
        "device_class": None,
        "type": "cop"
    },
    {
        "name": "Last Defrost/Restart",
        "unique_id": f"{UNIQUE_ID_PREFIX}last_defrost_restart",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "trigger_address": 34
    },
    {
        "name": "Last Compressor Run",
        "unique_id": f"{UNIQUE_ID_PREFIX}last_compressor_run",
        "unit": None,
        "device_class": "timestamp",
        "type": "last_triggered",
        "trigger_address": 30
    }
]

# Diagnose Sensoren

BINARY_SENSORS = [
    {
        "name": "Unit error",
        "address": 20,
        "device_class": "problem",
        "entity_category": "diagnostic"
    },
    {
        "name": "Circulation pump running",
        "address": 29,
        "device_class": "running",
        "entity_category": "diagnostic"
    },
    {
        "name": "Compressor run",
        "address": 30,
        "device_class": "running",
        "entity_category": "diagnostic"
    },
    {
        "name": "Booster heater run",
        "address": 31,
        "device_class": "running",
        "entity_category": "diagnostic"
    },
    {
        "name": "Disinfection operation",
        "address": 32,
        "device_class": "running",
        "entity_category": "diagnostic"
    },
    {
        "name": "Defrost/Restart",
        "address": 34,
        "device_class": "running",
        "entity_category": "diagnostic"
    },
    {
        "name": "Hot start",
        "address": 35,
        "device_class": "running",
        "entity_category": "diagnostic"
    },
    {
        "name": "Holiday mode",
        "address": 63,
        "device_class": "running",
        "entity_category": "diagnostic"
    }
]
