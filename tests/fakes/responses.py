"""Demo register data for testing."""


def generate_demo_register_data():
    """Generate realistic demo register data for testing.

    Returns:
        Dict with input_registers, holding_registers, discrete_inputs, coils lists.
    """
    # Input registers (addresses 0-87)
    input_registers = [32766] * 88  # Default: unavailable
    input_registers[1] = 3240  # Leaving water temp: 32.4°C
    input_registers[2] = 3045  # Leaving water temp BUH: 30.45°C
    input_registers[3] = 2940  # Return water temp: 29.4°C
    input_registers[4] = 4540  # DHW temp: 45.0°C
    input_registers[5] = 1240  # Outside air temp: 12.0°C
    input_registers[6] = 1540  # Flow rate: 15.0 L/min
    input_registers[8] = 500  # Heat pump power: 500W
    input_registers[9] = 1  # Circulation pump running
    input_registers[10] = 1  # Compressor running
    input_registers[11] = 0  # Booster heater
    input_registers[31] = 1  # Compressor run
    input_registers[32] = 0  # Booster heater run
    input_registers[37] = 0  # 3-way valve: space heating
    input_registers[38] = 1  # Operation mode: heating
    input_registers[40] = 3250  # Leaving water PHE: 32.5°C
    input_registers[41] = 2750  # Leaving water BUH: 27.5°C
    input_registers[42] = 2850  # Return water: 28.5°C
    input_registers[43] = 2950  # DHW: 29.5°C
    input_registers[44] = 65036  # Outside air: -5.0°C (2's complement)
    input_registers[49] = 1540  # Flow rate: 15.0 L/min
    input_registers[51] = 45  # Heat pump power: 0.45 kW
    input_registers[52] = 1  # DHW normal operation
    input_registers[53] = 1  # Space heating/cooling operation
    input_registers[63] = 0  # Disinfection state: unsuccessful
    input_registers[65] = 0  # Demand response: free
    input_registers[79] = 90  # Water pressure: 0.9 bar
    input_registers[80] = 2200  # Target Main zone: 22.0°C
    input_registers[81] = 2000  # Target Add zone: 20.0°C
    input_registers[82] = 0  # Abnormality counter
    input_registers[84] = 1200  # Room Heating lower: 12.0°C
    input_registers[85] = 3000  # Room Heating upper: 30.0°C
    input_registers[86] = 1200  # Room Cooling lower: 12.0°C
    input_registers[87] = 3500  # Room Cooling upper: 35.0°C

    # Holding registers (addresses 0-80)
    holding_registers = [0] * 81
    holding_registers[1] = 2500  # Main Heating setpoint: 25.0°C
    holding_registers[2] = 1800  # Main Cooling setpoint: 18.0°C
    holding_registers[3] = 1  # Operation mode: heating
    holding_registers[4] = 1  # Space heating/cooling ON: on
    holding_registers[6] = 2100  # Room Thermostat Heating Main: 21.0°C
    holding_registers[7] = 2400  # Room Thermostat Cooling Main: 24.0°C
    holding_registers[9] = 0  # Quiet mode: off
    holding_registers[10] = 4800  # DHW reheat setpoint: 48.0°C
    holding_registers[54] = 0  # Main LWT Heating offset
    holding_registers[55] = 0  # Main LWT Cooling offset
    holding_registers[56] = 0  # Smart Grid: free running
    holding_registers[58] = 500  # Imposed power limit: 5.0 kW
    holding_registers[63] = 3500  # Add Heating setpoint: 35.0°C
    holding_registers[64] = 1800  # Add Cooling setpoint: 18.0°C
    holding_registers[66] = 0  # Add LWT Heating offset
    holding_registers[67] = 0  # Add LWT Cooling offset
    holding_registers[68] = 0  # Weather-dependent Heating: fixed
    holding_registers[69] = 0  # Weather-dependent Cooling: fixed
    holding_registers[74] = 0  # Thermostat Request Main: none
    holding_registers[75] = 0  # Thermostat Request Add: none
    holding_registers[76] = 2100  # Room Thermostat Heating Main
    holding_registers[77] = 2400  # Room Thermostat Cooling Main
    holding_registers[78] = 2000  # Room Thermostat Heating Add
    holding_registers[79] = 2300  # Room Thermostat Cooling Add
    holding_registers[80] = 0  # DHW mode: reheat

    # Discrete inputs (addresses 0-26)
    discrete_inputs = [False] * 27
    discrete_inputs[1] = True  # Shut-off valve
    discrete_inputs[2] = False  # Second discrete input
    discrete_inputs[11] = True  # Compressor running
    discrete_inputs[19] = True  # DHW running
    discrete_inputs[20] = True  # Main zone running
    discrete_inputs[25] = True  # Circulation pump running

    # Coils (addresses 0-3)
    coils = [False] * 4
    coils[1] = True  # DHW ON
    coils[2] = False  # Main zone OFF
    coils[3] = False  # Additional zone OFF

    return {
        "input_registers": input_registers,
        "holding_registers": holding_registers,
        "discrete_inputs": discrete_inputs,
        "coils": coils,
    }
