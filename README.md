![CI](https://github.com/joklee/ha_daikin_altherma4_modbus/actions/workflows/ci.yml/badge.svg)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/joklee/ha_daikin_altherma4_modbus)
![GitHub all releases](https://img.shields.io/github/downloads/joklee/ha_daikin_altherma4_modbus/total)
![GitHub stars](https://img.shields.io/github/stars/joklee/ha_daikin_altherma4_modbus?style=social)
![GitHub forks](https://img.shields.io/github/forks/joklee/ha_daikin_altherma4_modbus?style=social)
![GitHub issues](https://img.shields.io/github/issues/joklee/ha_daikin_altherma4_modbus)
![GitHub pull requests](https://img.shields.io/github/issues-pr/joklee/ha_daikin_altherma4_modbus)
![License](https://img.shields.io/github/license/joklee/ha_daikin_altherma4_modbus)
![HACS](https://img.shields.io/badge/HACS-Default-orange)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)

# Daikin Altherma 4 Modbus Integration for Home Assistant

**⚠️ WARNING: Use at your own risk! This integration modifies heat pump settings. Incorrect configuration may damage your equipment or void warranty. Always consult the official Daikin documentation before making changes.**

**Note: Not all registers may provide valid values depending on your heat pump model and configuration. Some registers might return zero, error codes, or unexpected values. Always verify values against your heat pump's display or official documentation.**


## Daikin Altherma 4 Modbus Activation

Before using this integration, you need to enable Modbus TCP communication on your Daikin Altherma 4 heat pump.

### Modbus TCP/IP for Daikin Altherma

**NOTICE**: If the unit receives commands from both Modbus and Cloud interfaces, it will execute the command that was received most recently.

#### Modbus Protocol
The following Modbus protocol can be used:
- Modbus TCP/IP

**Modbus TCP/IP Parameters:**
- **Network**: Ethernet (Wifi not supported)
- **Port**:
  - No encryption: 502
  - TLS encryption: 802 (not tested)
- **IP Address**: IP address of Daikin Altherma 4

**Change-based Algorithm**
The Modbus algorithm is change based. This means the unit is only updated if a change in configuration is detected. To prevent changes being lost due to communication outages, it is recommended to periodically refresh the state from client side.

**Connection Limits**
**INFORMATION**: A total of 3 concurrent connections is possible.
Examples:
- 3x using the 502 port
- 3x using the 802 port
- Combination of both, e.g. 1x 502 and 2x 802

### Prerequisites
- Daikin Altherma 4 heat pump (EPSX series)
- MMI Version 2.2.0 or higher
- Access to the heat pump's controller interface
- Network connection over Ethernet/RJ45 to the heat pump

### Step-by-Step Activation

This custom integration allows you to monitor and control your Daikin Altherma 4 heat pump via Modbus TCP.

## Features

### Device Organization
The integration organizes entities into logical device groups:
- **Input Register**: Basic monitoring and status sensors (112 registers)
- **Holding Register**: Configurable parameters and setpoints
- **Enhanced**: Calculated sensors, thermostats, and advanced features
- **Discrete Input**: Binary status indicators
- **Coil**: Switchable control functions

### Sensors (Input Registers)
- **Error Monitoring**: Unit error, error codes, and sub-codes
- **Operational Status**: 3-way valve position, operation mode
- **Temperature Sensors**:
  - Leaving water temperature (PHE, BUH)
  - Return water temperature
  - DHW temperature
  - Outside air temperature
  - Liquid refrigerant temperature
  - Remote controller room temperature (Main & Add)
  - Mixing kit temperatures
  - PrePHE outdoor temperature
  - Tank valve temperatures
- **Performance Metrics**:
  - Flow rate
  - Heat pump power consumption
  - Water pressure
- **System Status**:
  - DHW and space heating/cooling operation
  - Various setpoints and valve positions
  - Pump speeds and PWM values
  - Disinfection and demand response modes
  - Abnormality counter
- **Room Setpoints**:
  - Room heating setpoint limits (lower/upper)
  - Room cooling setpoint limits (lower/upper)
  - Space heating/cooling targets (Main/Add zones)

### Binary Sensors (Diagnostic)
- **Input Register Diagnostics**:
  - Circulation pump running status
  - Compressor run status
  - Booster heater run status
  - Disinfection operation
  - Defrost/Restart cycles
  - Hot start detection
  - Disinfection state
- **Discrete Input Diagnostics**:
  - Shut-off valve status
  - Backup heater relays (1-6)
  - Auxiliary heating status
  - Storage tank status
  - Bivalent operation
  - Compressor running
  - Quiet mode operation
  - Holiday mode active
  - Antifrost status
  - Water pipe freeze prevention
  - DHW running
  - Main/Additional zone running
  - Powerful/Manual tank heat up requests
  - Emergency active
  - Imposed limit acceptance

### Climate Entities (Enhanced)
- **Heating Thermostat Control**: Main zone temperature control with operation modes
- **DHW Thermostat Control**: Domestic hot water manual heat-up control

### Calculated Sensors (Enhanced)
- **Heat Pump Power Calculated**: Real-time calculation of heat pump power consumption based on electrical measurements
- **Coefficient of Performance (CoP)**: Efficiency ratio showing thermal output vs electrical input
- **Delta-T**: Temperature difference between supply and return water (system efficiency indicator)
- **Last Compressor Run**: Timestamp of the most recent compressor activation
- **Last Defrost**: Timestamp of the most recent defrost cycle completion
- **Last Booster Heater**: Timestamp of the most recent auxiliary heater activation
- **Last DHW Running**: Timestamp of the most recent domestic hot water heating cycle
- **External Electric Power**: Integration with external power sensors for enhanced monitoring

### Number Entities (Holding Register)
- **Temperature Setpoints**: Main/additional heating and cooling setpoints
- **Operation Modes**: System operation mode, space heating/cooling control
- **Room Thermostat Control**: Temperature setpoints for main and additional zones
- **Special Modes**: Quiet mode operation, DHW settings
- **Advanced Settings**: Weather-dependent modes, smart grid operation, power limits

### Switch Entities (Coil Register)
- **Domestic Hot Water**: DHW ON/OFF control
- **Main Zone**: Main zone heating control
- **Additional Zone**: Additional zone heating control

### Select Entities (Input & Holding Register)
- **3-Way Valve**: Space heating vs DHW mode selection
- **Unit Operation Mode**: Stop, Tank Heat Up, Space heating, Space cooling, Actuator
- **Operation Mode**: System operation mode selection with enum options
- **DHW Mode Setting**: Reheat, Schedule and reheat, Scheduled

## Multilingual Support

The integration supports multiple languages with full translation support:
- **English**: Default language with comprehensive translations
- **German**: Complete German translations for all entities
- **Translation Keys**: All entities use translation keys for consistent localization

### Translation Features
- All sensor names are translatable
- Binary sensor states are properly localized
- Device categories and entity names are language-aware
- Consistent translations across all entity types

## Testing & Development

### Comprehensive Test Suite
- **49 automated tests** covering core functionality
- **Mock client** for development without hardware
- **Coverage reporting** for quality assurance
- **Integration tests** for full workflow validation

### Test Coverage
- **Core components**: 100% coverage for constants, 71% for client interfaces
- **Mock client**: Realistic data generation for all register types
- **Error handling**: Comprehensive error scenario testing
- **Translation validation**: Multi-language support verification

### Development Features
- **Demo mode**: Built-in mock client for testing
- **Debug logging**: Comprehensive logging for troubleshooting
- **Modular architecture**: Clean separation of concerns
- **Type hints**: Full type annotation support

## Installation

### HACS Installation (Recommended)
1. Open Home Assistant
2. Go to **HACS** → **Integrations**
3. Click the three dots menu → **Custom repositories**
4. Add this repository URL: `https://github.com/joklee/ha_daikin_altherma4_modbus`
5. Restart Home Assistant
6. Go to **Settings** → **Devices & Services** → **Integrations**
7. Click **+ Add Integration** → search for "Daikin Altherma 4 Modbus"
8. Configure the integration with your heat pump's IP address and port

### Manual Installation
1. Copy the `custom_components/ha_daikin_altherma4_modbus` folder to your `config/custom_components` directory
2. Restart Home Assistant
3. Follow steps 6-8 from HACS installation above

## Configuration

### Required Parameters
- **Connection**: Only ethernet cable
- **Host**: IP address of your Daikin heat pump
- **Port**: Modbus TCP port (default: 502)
- **Scan Interval**: Update frequency in seconds (default: 15)

### Optional Parameters
- **Electric Power Sensor Entity ID**: Reference sensor for enhanced power calculations and CoP monitoring

#### External Electric Power Sensor Configuration
The **External Electric Power Sensor Entity ID** parameter allows you to integrate an external power measurement sensor for more accurate energy monitoring:

**Purpose:**
- Enhances the calculated **Coefficient of Performance (CoP)** with real electrical power data
- Improves **Heat Pump Power Calculated** accuracy
- Enables comprehensive energy consumption tracking
- Provides real-time efficiency monitoring

**Compatible Sensors:**
- **Smart Plugs**: Shelly, TP-Link Kasa, Sonoff POW (recommended for whole house monitoring)
- **Energy Meters**: Modbus power sensors, DIN-rail energy meters
- **Home Assistant Energy**: Built-in energy monitoring sensors
- **Any sensor** providing power measurements in **Watts (W)**

**Recommended Setup Options:**

**Option 1: Whole House Monitoring (Recommended)**
```
Electric Power Sensor Entity ID: sensor.shelly_em_power
```
- **Measures**: Total house power consumption including heat pump
- **Benefits**: Complete energy overview, accurate overall CoP
- **Best for**: Understanding total system efficiency

**Option 2: Heat Pump Only Monitoring**
```
Electric Power Sensor Entity ID: sensor.modbus_heatpump_power
```
- **Measures**: Only heat pump electrical consumption
- **Benefits**: Pure heat pump efficiency calculation
- **Best for**: Technical analysis and optimization

**Option 3: Sub-metered Monitoring**
```
Electric Power Sensor Entity ID: sensor.heat_pump_circuit_power
```
- **Measures**: Dedicated circuit for heat pump only
- **Benefits**: Isolated measurement
- **Best for**: Precise heat pump performance analysis

**How to Configure:**
1. **Install your power sensor** (smart plug, energy meter, etc.)
2. **Add to Home Assistant** if not already integrated
3. **Find the entity ID** in Developer Tools → States
4. **Enter the full entity ID** in the integration configuration
5. **Verify the sensor** provides power readings in Watts

**Configuration Examples:**
```
# Shelly EM (Whole House)
sensor.shelly_em_power

# Shelly Plug (Heat Pump Only)
sensor.shelly_plug_power

# Modbus Energy Meter
sensor.modbus_electric_power

# Home Assistant Energy
sensor.total_home_power
```

**Benefits When Configured:**
- **Accurate CoP**: Real-time efficiency calculation (thermal power ÷ electrical power)
- **Energy Dashboard**: Integration with Home Assistant Energy monitoring
- **Cost Tracking**: Calculate actual heating costs
- **Performance Alerts**: Monitor efficiency drops or issues
- **Historical Analysis**: Track efficiency over time and seasons

**Technical Details:**
- **Required Unit**: Watts (W)
- **Update Frequency**: Should match or exceed integration scan interval
- **Accuracy**: ±1% recommended for reliable CoP calculations
- **Range**: Should cover expected power consumption (typically 1-10kW for heat pumps)

**Troubleshooting:**
- **Sensor not found**: Verify entity ID in Developer Tools → States
- **Wrong units**: Ensure sensor reports in Watts, not kW or VA
- **No CoP data**: Check if power sensor is updating regularly
- **Inaccurate readings**: Calibrate or verify sensor accuracy

**Advanced Usage:**
- **Multiple sensors**: Use template sensors to combine measurements
- **Conditional logic**: Automate based on efficiency thresholds
- **Integration**: Combine with energy storage or solar monitoring

## Register Reference

### Input Registers (21-87)

| Address | Name                                   | Unit | Scale | Type | Range |
|---------|----------------------------------------|------|-------|------|-------|
| 21      | Unit abnormality                       | - | 1 | int16 | 0: No error, 1: Fault, 2: Warning |
| 22      | Unit abnormality code                  | - | 1 | string | 2 ASCII characters |
| 23      | Unit abnormality sub code              | - | 1 | int16 | 0~99 (32766: No error) |
| 30      | Circulation pump running               | - | 1 | int16 | 0: OFF, 1: ON |
| 31      | Compressor run                         | - | 1 | int16 | 0: OFF, 1: ON |
| 32      | Booster heater run                     | - | 1 | int16 | 0: OFF, 1: ON |
| 33      | Disinfection operation                 | - | 1 | int16 | 0: OFF, 1: ON |
| 35      | Defrost/Restart                        | - | 1 | int16 | 0: OFF, 1: ON |
| 36      | Hot start                              | - | 1 | int16 | 0: OFF, 1: ON |
| 37      | 3-way valve                            | - | 1 | int16 | 0: Space heating, 1: DHW |
| 38      | Operation mode                         | - | 1 | int16 | 0: None, 1: Heating, 2: Cooling |
| 40      | Leaving water temperature PHE          | °C | 0.01 | int16 | -100.00~100.00°C |
| 41      | Leaving water temperature BUH          | °C | 0.01 | int16 | -100.00~100.00°C |
| 42      | Return water temperature               | °C | 0.01 | int16 | -100.00~100.00°C |
| 43      | Domestic Hot Water temperature         | °C | 0.01 | int16 | -100.00~100.00°C |
| 44      | Outside air temperature                | °C | 0.01 | int16 | -100.00~100.00°C |
| 45      | Liquid refrigerant temperature         | °C | 0.01 | int16 | -100.00~100.00°C |
| 49      | Flow rate                              | L/min | 0.01 | int16 | 0~100 L/min |
| 50      | Remote control room temperature (Main) | °C | 0.01 | int16 | -100.00~100.00°C |
| 51      | Heat pump power consumption            | kW | 0.01 | int16 | 0~20.00 kW |
| 52      | DHW normal operation                   | - | 1 | int16 | 0: Idle/Buffering, 1: Operation |
| 53      | Space heating/cooling normal operation | - | 1 | int16 | 0: Idle/Buffering, 1: Operation |
| 54      | Leaving water Main Heating setpoint lower | °C | 0.01 | int16 | 15~85°C |
| 55      | Leaving water Main Heating setpoint upper | °C | 0.01 | int16 | 15~85°C |
| 56      | Leaving water Main Cooling setpoint lower | °C | 0.01 | int16 | 5~22°C |
| 57      | Leaving water Main Cooling setpoint upper | °C | 0.01 | int16 | 5~22°C |
| 58      | Leaving water Add Heating setpoint lower | °C | 0.01 | int16 | 15~85°C |
| 59      | Leaving water Add Heating setpoint upper | °C | 0.01 | int16 | 15~85°C |
| 60      | Leaving water Add Cooling setpoint lower | °C | 0.01 | int16 | 5~22°C |
| 61      | Leaving water Add Cooling setpoint upper | °C | 0.01 | int16 | 5~22°C |
| 63      | Disinfection state                    | - | 1 | int16 | 0: Unsuccessful, 1: Successful, 2: Maintain, 3: Heat Up |
| 64      | Holiday mode                           | - | 1 | int16 | 0: OFF, 1: ON |
| 65      | Demand response mode                   | - | 1 | int16 | 0: Free, 1: Forced Off, 2: Forced On, 3: Recommended On, 4: Reduced |
| 66      | Bypass valve position                  | % | 1 | int16 | 0~100% |
| 67      | Tank valve position                    | % | 1 | int16 | 0~100% |
| 68      | Circulation pump speed                 | % | 1 | int16 | 0~100 L/min |
| 69      | Mixed pump PWM                         | % | 1 | int16 | 0~100% |
| 70      | Direct pump PWM                        | % | 1 | int16 | 0~100% |
| 71      | Mixing valve position in mixing kit    | % | 1 | int16 | 0~100% |
| 72      | Mixing Leaving water temperature in mixing kit | °C | 0.01 | int16 | -100.00~100.00°C |
| 73      | Space heating/cooling target for Main zone in mixing kit | °C | 0.01 | int16 | -100.00~100.00°C |
| 74      | Leaving water temperature prePHE outdoor | °C | 0.01 | int16 | -128.99~128.99°C |
| 75      | Leaving water temperature Tank valve   | °C | 0.01 | int16 | -127.00~127.00°C |
| 76      | Domestic Hot Water Upper temperature  | °C | 0.01 | int16 | -127.00~127.00°C |
| 77      | Domestic Hot Water Lower temperature  | °C | 0.01 | int16 | -127.00~127.00°C |
| 78      | Remote controller room temperature (Add) | °C | 0.01 | int16 | -100.00~100.00°C |
| 79      | Water pressure                         | bar | 0.01 | int16 | 10~600 bar |
| 80      | Space heating/cooling target for Main zone | °C | 0.01 | int16 | -127.00~127.00°C |
| 81      | Space heating/cooling target for Add zone | °C | 0.01 | int16 | -127.00~127.00°C |
| 82      | Abnormality counter (user)            | - | 1 | int16 | 0~200 |
| 83      | Unit operation mode                   | - | 1 | int16 | 0: Stop, 1: Tank Heat Up, 2: Space heating, 3: Space cooling, 4: Actuator |
| 84      | Room Heating setpoint Lower limit     | °C | 0.01 | int16 | 12.00~30.00°C |
| 85      | Room Heating setpoint Upper limit     | °C | 0.01 | int16 | 12.00~30.00°C |
| 86      | Room Cooling setpoint Lower limit     | °C | 0.01 | int16 | 12.00~35.00°C |
| 87      | Room Cooling setpoint Upper limit     | °C | 0.01 | int16 | 12.00~35.00°C |

### Holding Registers

| Address | Name                                                    | Unit | Scale | Type | Range |
|---------|---------------------------------------------------------|------|-------|------|-------|
| 1 | Leaving water Main Heating setpoint                     | °C | 1 | int16 | 0~100°C |
| 2 | Leaving water Main Cooling setpoint                     | °C | 1 | int16 | 0~100°C |
| 3 | Operation mode select                                   | - | 1 | int16 | 0: Auto, 1: Heating, 2: Cooling |
| 4 | Space heating/cooling ON/OFF                            | - | 1 | int16 | 0: OFF, 1: ON |
| 6 | Room Thermostat Heating Setpoint Main                   | °C | 1 | int16 | 12~30°C |
| 7 | Room Thermostat Cooling Setpoint Main                   | °C | 1 | int16 | 12~35°C |
| 9 | Quiet mode operation                                    | - | 1 | int16 | 0: OFF, 1: ON (Automatic), 2: ON (Manual) |
| 10 | DHW reheat setpoint                                     | °C | 1 | int16 | 30~85°C |
| 13 | DHW booster mode ON/OFF (Powerful)                      | - | 1 | int16 | 0: OFF, 1: ON |
| 14 | DHW boost setpoint (Powerful)                           | °C | 0.01 | Temp16 | 30~85°C |
| 15 | DHW Single heat-up ON/OFF (Manual)                      | - | 1 | int16 | 0: OFF, 1: ON |
| 16 | DHW Single Heat-up Setpoint (Manual)                    | °C | 0.01 | Temp16 | 30~85°C |
| 54 | Weather-dependent mode Main LWT Heating setpoint offset | °C | 1 | int16 | -10~10°C |
| 55 | Weather-dependent mode Main LWT Cooling setpoint offset | °C | 1 | int16 | -10~10°C |
| 56 | Smart Grid Operation Mode                               | - | 1 | int16 | 0: Free running, 1: Forced off, 2: Recommended on, 3: Forced on |
| 58 | Imposed power limit                                     | kW | 0.01 | Pow16 | 0~20 kW |
| 63 | Leaving water Add Heating setpoint                      | °C | 1 | int16 | 3~85°C |
| 64 | Leaving water Add Cooling setpoint                      | °C | 1 | int16 | 3~85°C |
| 66 | Weather-dependent mode Add LWT Heating setpoint offset  | °C | 1 | int16 | -10~10°C |
| 67 | Weather-dependent mode Add LWT Cooling setpoint offset  | °C | 1 | int16 | -10~10°C |
| 68 | Weather-dependent mode Heating Main                     | - | 1 | int16 | 0: Fixed, 1: Weather dependent |
| 69 | Weather-dependent mode Cooling Main                     | - | 1 | int16 | 0: Fixed, 1: Weather dependent |
| 74 | Thermostat Request Main                                 | - | 1 | int16 | 0: None, 1: Heating, 2: Cooling |
| 75 | Thermostat Request Additional                           | - | 1 | int16 | 0: None, 1: Heating, 2: Cooling |
| 76 | Room Thermostat control Heating Setpoint Main           | °C | 0.01 | Temp16 | 12.00~30.00°C |
| 77 | Room Thermostat control Cooling Setpoint Main           | °C | 0.01 | Temp16 | 12.00~35.00°C |
| 78 | Room thermostat control Heating setpoint Add            | °C | 0.01 | Temp16 | 12.00~30.00°C |
| 79 | Room thermostat control Cooling setpoint Add            | °C | 0.01 | Temp16 | 12.00~35.00°C |
| 80 | DHW mode setting                                        | - | 1 | int16 | 0: Reheat, 1: Schedule and reheat, 2: Scheduled, 32766: Off |

### Discrete Inputs (1-26)

| Address | Name | Type | Range |
|---------|------|------|-------|
| 1 | Shut-off valve | bit | 0~1 |
| 2 | Backup heater relay 1 | bit | 0~1 |
| 3 | Backup heater relay 2 | bit | 0~1 |
| 4 | Backup heater relay 3 | bit | 0~1 |
| 5 | Backup heater relay 4 | bit | 0~1 |
| 6 | Backup heater relay 5 | bit | 0~1 |
| 7 | Backup heater relay 6 | bit | 0~1 |
| 8 | Booster heater | bit | 0~1 |
| 9 | Tank boiler | bit | 0~1 |
| 10 | Bivalent | bit | 0~1 |
| 11 | Compressor running | bit | 0~1 |
| 12 | Quiet mode operation active | bit | 0~1 |
| 13 | Holiday mode active | bit | 0~1 |
| 14 | Antifrost status | bit | 0~1 |
| 15 | Water pipe freeze prevention status | bit | 0~1 |
| 16 | Disinfection operation | bit | 0~1 |
| 17 | Defrost | bit | 0~1 |
| 18 | Hot start | bit | 0~1 |
| 19 | DHW running | bit | 0~1 |
| 20 | Main zone running | bit | 0~1 |
| 21 | Additional zone running | bit | 0~1 |
| 22 | Powerful tank heat up request | bit | 0~1 |
| 23 | Manual tank heat up request | bit | 0~1 |
| 24 | Emergency active | bit | 0~1 |
| 25 | Circulation pump running | bit | 0~1 |
| 26 | Imposed limit acceptance | bit | 0~1 |

### Coil Registers (1-3)

| Address | Name | Type | Range |
|---------|------|------|-------|
| 1 | Domestic Hot Water ON/OFF | bit | 0~1 |
| 2 | Main zone ON/OFF | bit | 0~1 |
| 3 | Additional zone ON/OFF | bit | 0~1 |

### Options Flow
After installation, you can configure the external electric power sensor through:
1. **Settings** → **Devices & Services**
2. Find your Daikin Altherma 4 Modbus integration
3. Click **Configure** to access options
4. Add or modify the external power sensor entity ID

## Register Support

This integration supports comprehensive Modbus register coverage:

- **Input Registers (Read-only)**: 112 monitoring and status values
  - Addresses 21-87: Complete sensor coverage
  - Temperature sensors, operational status, error monitoring
  - Performance metrics and diagnostic counters
- **Binary Sensors**: Status and error detection (Input and Discrete Input)
- **Coil Registers (Writeable)**: ON/OFF control functions
- **Holding Registers (Writeable)**: Configurable setpoints and parameters
- **Climate Entities**: Advanced thermostat control
- **Number Entities**: Precise numerical control
- **Select Entities**: Enum-based selection controls (20 select entities)

### Complete Input Register Coverage
✅ **All 16 requested input registers now supported:**
- Addresses 72-77: Mixing kit and DHW temperatures
- Address 78: Remote controller room temperature (Add)
- Address 79: Water pressure
- Address 80: Space heating/cooling target for Main zone Temp16
- Address 81: Space heating/cooling target for Add zone
- Address 82: Abnormality counter (user)
- Address 83: Unit operation mode (select entity)
- Addresses 84-87: Room heating/cooling setpoint limits

## Troubleshooting

### Common Issues
- **Connection Failed**: Verify IP address and port
- **No Data**: Check Modbus TCP settings on your heat pump
- **Update Errors**: Ensure scan interval is appropriate (minimum 10 seconds)
- **Translation Issues**: Ensure proper language settings in Home Assistant
- **3-Way Valve Not Available**: Verify select entity configuration

### Connection & Network Issues
- **Device Offline**: Integration automatically retries connections and gracefully handles offline devices
- **Network Interruption**: Automatic reconnection with exponential backoff (max 30 seconds delay)
- **Timeout Errors**: Retry logic with 2-3 attempts before reporting failure
- **Multiple Connections**: Daikin supports max 3 concurrent Modbus connections

### Error Recovery Behavior
- **Connection Loss**: Integration attempts automatic reconnection without user intervention
- **Temporary Failures**: Short-term network issues are handled transparently
- **Persistent Failures**: After multiple failed attempts, entities show unavailable state
- **Log Management**: Errors are logged at appropriate levels without spamming logs

### Performance Issues
- **High Scan Frequency**: Reduce scan intervals if experiencing performance issues
- **Network Latency**: Use wired Ethernet connection for best performance
- **Register Access**: Some registers may be unsupported depending on heat pump model
- **Connection Pooling**: Integration uses optimized connection pooling for better performance
- **Batch Operations**: Register reads are batched for optimal Modbus efficiency

### Debug Mode
Enable debug logging in your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ha_daikin_altherma4_modbus: debug
```

### Advanced Troubleshooting
- **Modbus Register Validation**: Use demo mode (host: localhost) to test integration logic
- **Network Testing**: Verify connectivity with `telnet <heat-pump-ip> 502`
- **Register Coverage**: Check device documentation for supported register ranges
- **Performance Monitoring**: Monitor Home Assistant logs for connection patterns

### Testing Without Hardware
Use the built-in mock client for development and testing:
- Set host to "localhost" in configuration
- Integration will use realistic mock data
- All 112 input registers generate realistic values
- Perfect for development and demonstration

## Supported Devices

This integration supports Daikin Altherma 4 heat pumps with Modbus TCP communication:

### Compatible Models
- **EPBX07A**
- **EPBX10A**  
- **EPBX14A**
- **EPSX07P30A**
- **EPSX07P50A**
- **EPSX(B)10P30A**
- **EPSX(B)10P50A**
- **EPSX10P50AF**
- **EPSX(B)14P30A**
- **EPSX(B)14P50A**
- **EPSXB07P30A**
- **EPSXB07P50A**
- **EPVX07S(U)18A**
- **EPVX07S(U)23A**
- **EPVX10S(U)18A**
- **EPVX10S(U)23A**
- **EPVX14S(U)18A**
- **EPVX14S(U)23A**
- **EPVZ07S18A**
- **EPVZ07S23A**
- **EPVZ10S18A**
- **EPVZ10S23A**
- **EPVZ14S18A**
- **EPVZ14S23A**

### Technical Requirements
- **Modbus TCP communication protocol**
- **MMI Version 2.2.0 or higher**
- **Ethernet connection** (WiFi not supported)
- **Port 502** (unencrypted) or **Port 802** (TLS encryption)

### Features
- Full register coverage for complete monitoring
- All 112 input registers supported
- Control functions via holding registers and coils
- Comprehensive error monitoring and diagnostics
- Multi-language support (English, German)

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

### Development Setup
- Install test requirements: `pip install -r requirements-test.txt`
- Run tests: `make test-unit` or `python -m pytest tests/ --cov=custom_components/ha_daikin_altherma4_modbus`
- Use mock client for development without hardware
- Run full CI pipeline locally: `make ci-local`
- Code quality checks: `make lint` and `make format-check`
- Performance benchmarks: `make benchmark`

### Testing
The project includes a comprehensive test suite with 133 tests:
- **Unit tests**: Core functionality testing
- **Integration tests**: End-to-end workflow testing  
- **Performance tests**: Connection pooling and optimization validation
- **Mock client testing**: Development without physical hardware
- **Coverage reporting**: 26% code coverage with detailed reports

## License

This project is licensed under the GPL-3.0-or-later License. See the [LICENSE](LICENSE) file for details.

## Credits

- Based on Daikin Altherma HT Modbus documentation
- Built with Home Assistant custom integration framework
- Uses pymodbus library for Modbus TCP communication
- Multilingual support with comprehensive translations
- Comprehensive test coverage with mock client support
- Performance optimizations with connection pooling
- Automated CI/CD pipeline with quality gates
