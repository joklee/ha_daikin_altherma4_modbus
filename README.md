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

| Address | Name | Description | Unit | Scale | Type |
|---------|------|-------------|------|-------|------|
| 21      | Unit abnormality | Error status | - | 1 | int16 |
| 22      | Unit abnormality code | Specific error code | - | 1 | string |
| 23      | Unit abnormality sub code | Error sub-code | - | 1 | uint16 |
| 30      | Circulation pump running | Pump status | - | 1 | uint16 |
| 31      | Compressor run | Compressor status | - | 1 | uint16 |
| 32      | Booster heater run | Auxiliary heating | - | 1 | uint16 |
| 33      | Disinfection operation | Disinfection status | - | 1 | uint16 |
| 35      | Defrost/Restart | Defrost cycle status | - | 1 | uint16 |
| 36      | Hot start | Hot start status | - | 1 | uint16 |
| 37      | 3-way valve | Valve position | - | 1 | uint16 |
| 38      | Operation mode | Current operation mode | - | 1 | uint16 |
| 40      | Leaving water temperature PHE | Primary heat exchanger | °C | 0.01 | int16 |
| 41      | Leaving water temperature BUH | Backup heater | °C | 0.01 | int16 |
| 42      | Return water temperature | Return flow | °C | 0.01 | int16 |
| 43      | Domestic Hot Water temperature | Domestic hot water | °C | 0.01 | int16 |
| 44      | Outside air temperature | Ambient temperature | °C | 0.01 | int16 |
| 45      | Liquid refrigerant temperature | Refrigerant temp | °C | 0.01 | int16 |
| 49      | Flow rate | Water flow rate | L/min | 0.01 | uint16 |
| 50      | Remote control room temperature (Main) | Main zone temp | °C | 0.01 | int16 |
| 51      | Heat pump power consumption | Electrical power | W | 10 | uint16 |
| 52      | DHW normal operation | DHW operation status | - | 1 | uint16 |
| 53      | Space heating/cooling normal operation | Space operation | - | 1 | uint16 |
| 58      | Leaving water Add Heating setpoint lower | Add heat limit lower | °C | 0.01 | int16 |
| 59      | Leaving water Add Heating setpoint upper | Add heat limit upper | °C | 0.01 | int16 |
| 60      | Leaving water Add Cooling setpoint lower | Add cool limit lower | °C | 0.01 | int16 |
| 61      | Leaving water Add Cooling setpoint upper | Add cool limit upper | °C | 0.01 | int16 |
| 63      | Disinfection state | Disinfection status | - | 1 | uint16 |
| 64      | Holiday mode | Holiday status | - | 1 | uint16 |
| 65      | Demand response mode | Demand response | - | 1 | uint16 |
| 66      | Bypass valve position | Bypass valve | % | 1 | uint16 |
| 67      | Tank valve position | Tank valve | % | 1 | uint16 |
| 68      | Circulation pump speed | Circulation pump | L/min | 1 | uint16 |
| 69      | Mixed pump PWM | Mixed pump | % | 1 | uint16 |
| 70      | Direct pump PWM | Direct pump | % | 1 | uint16 |
| 71      | Mixing valve position in mixing kit | Mixing valve | % | 1 | uint16 |
| 72      | Mixing Leaving water temperature in mixing kit | Mixing LWT | °C | 0.01 | int16 |
| 73      | Space heating/cooling target for Main zone in mixing kit | Mixing target | °C | 0.01 | int16 |
| 74      | Leaving water temperature prePHE outdoor | prePHE outdoor | °C | 0.01 | int16 |
| 75      | Leaving water temperature Tank valve | Tank valve LWT | °C | 0.01 | int16 |
| 76      | Domestic Hot Water Upper temperature | DHW upper | °C | 0.01 | int16 |
| 77      | Domestic Hot Water Lower temperature | DHW lower | °C | 0.01 | int16 |
| 78      | Remote controller room temperature (Add) | Add zone temp | °C | 0.01 | int16 |
| 79      | Water pressure | System pressure | bar | 0.01 | int16 |
| 80      | Space heating/cooling target for Main zone | Main zone target | °C | 0.01 | int16 |
| 81      | Space heating/cooling target for Add zone | Add zone target | °C | 0.01 | int16 |
| 82      | Abnormality counter (user) | User error counter | - | 1 | int16 |
| 83      | Unit operation mode | Operation mode select | - | 1 | uint16 |
| 84      | Room Heating setpoint Lower limit | Heat limit lower | °C | 0.01 | int16 |
| 85      | Room Heating setpoint Upper limit | Heat limit upper | °C | 0.01 | int16 |
| 86      | Room Cooling setpoint Lower limit | Cool limit lower | °C | 0.01 | int16 |
| 87      | Room Cooling setpoint Upper limit | Cool limit upper | °C | 0.01 | int16 |

### Holding Registers (1-60)

| Address | Name | Description | Unit | Scale | Type |
|---------|------|-------------|------|-------|------|
| 1 | Leaving water Main Heating setpoint | Main heating setpoint | °C | 0.01 | int16 |
| 2 | Leaving water Main Cooling setpoint | Main cooling setpoint | °C | 0.01 | int16 |
| 3 | Operation mode | System operation mode | - | 1 | uint16 |
| 4 | Space heating/cooling | Space heating/cooling control | - | 1 | uint16 |
| 5 | DHW temperature setpoint | DHW setpoint | °C | 0.01 | int16 |
| 6 | Room Thermostat Heating Setpoint Main | Room heating setpoint | °C | 0.01 | int16 |
| 7 | Room Thermostat Cooling Setpoint Main | Room cooling setpoint | °C | 0.01 | int16 |
| 9 | Quiet mode operation | Quiet mode setting | - | 1 | uint16 |
| 10 | DHW reheat setpoint | DHW reheat temperature | °C | 0.01 | int16 |
| 13 | DHW booster mode (Powerful) | DHW powerful mode | - | 1 | uint16 |
| 14 | DHW boost setpoint (Powerful) | DHW boost temperature | °C | 0.01 | int16 |
| 15 | DHW Single heat-up ON/OFF (Manual) | Manual DHW heating | - | 1 | int16 |
| 16 | DHW Single Heat-up Setpoint (Manual) | Manual DHW setpoint | °C | 0.01 | int16 |
| 54 | Weather-dependent mode Main LWT Heating offset | Heating offset | °C | 0.01 | int16 |
| 55 | Weather-dependent mode Main LWT Cooling offset | Cooling offset | °C | 0.01 | int16 |
| 56 | Smart Grid Operation Mode | Smart grid mode | - | 1 | uint16 |
| 58 | Imposed power limit | Power limitation | kW | 0.001 | uint16 |
| 63 | Leaving water Add Heating setpoint | Add heating setpoint | °C | 0.01 | int16 |
| 64 | Leaving water Add Cooling setpoint | Add cooling setpoint | °C | 0.01 | int16 |
| 66 | Weather-dependent mode Add LWT Heating offset | Add heating offset | °C | 0.01 | int16 |
| 67 | Weather-dependent mode Add LWT Cooling offset | Add cooling offset | °C | 0.01 | int16 |
| 68 | Weather-dependent mode Heating Main | Weather heating mode | - | 1 | uint16 |
| 69 | Weather-dependent mode Cooling Main | Weather cooling mode | - | 1 | uint16 |
| 74 | Thermostat Request Main | Main thermostat request | - | 1 | uint16 |
| 75 | Thermostat Request Additional | Add thermostat request | - | 1 | uint16 |
| 76 | Room Thermostat Heating Setpoint Main | Room heating setpoint | °C | 0.01 | int16 |
| 77 | Room Thermostat Cooling Setpoint Main | Room cooling setpoint | °C | 0.01 | int16 |
| 78 | Room thermostat control Heating setpoint Add | Add heating setpoint | °C | 0.01 | int16 |
| 79 | Room thermostat control Cooling setpoint Add | Add cooling setpoint | °C | 0.01 | int16 |
| 80 | DHW mode setting | DHW operation mode | - | 1 | int16 |

### Discrete Inputs (1-26)

| Address | Name | Description | Type |
|---------|------|-------------|------|
| 1 | Shut-off valve | Main valve status | Binary |
| 2 | Backup heater relay 1 | Backup heater 1 status | Binary |
| 3 | Backup heater relay 2 | Backup heater 2 status | Binary |
| 4 | Backup heater relay 3 | Backup heater 3 status | Binary |
| 5 | Backup heater relay 4 | Backup heater 4 status | Binary |
| 6 | Backup heater relay 5 | Backup heater 5 status | Binary |
| 7 | Backup heater relay 6 | Backup heater 6 status | Binary |
| 8 | Booster heater | Auxiliary heating | Binary |
| 9 | Tank boiler | Boiler status | Binary |
| 10 | Bivalent | Bivalent operation | Binary |
| 11 | Compressor running | Compressor status | Binary |
| 12 | Quiet mode operation active | Quiet mode status | Binary |
| 13 | Holiday mode active | Holiday status | Binary |
| 14 | Antifrost status | Antifrost operation | Binary |
| 15 | Water pipe freeze prevention status | Freeze prevention | Binary |
| 16 | Disinfection operation | Disinfection status | Binary |
| 17 | Defrost | Defrost cycle | Binary |
| 18 | Hot start | Hot start cycle | Binary |
| 19 | DHW running | Domestic hot water running | Binary |
| 20 | Main zone running | Main zone operation | Binary |
| 21 | Additional zone running | Add zone operation | Binary |
| 22 | Powerful tank heat up request | Tank heat up request | Binary |
| 23 | Manual tank heat up request | Manual tank request | Binary |
| 24 | Emergency active | Emergency status | Binary |
| 25 | Circulation pump running | Circulation pump | Binary |
| 26 | Imposed limit acceptance | Limit acceptance | Binary |

### Coil Registers (1-3)

| Address | Name | Description | Type |
|---------|------|-------------|------|
| 1 | Domestic Hot Water ON/OFF | Manual DHW heating | Coil |
| 2 | Main zone ON/OFF | Main zone control | Coil |
| 3 | Additional zone ON/OFF | Add zone control | Coil |

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
