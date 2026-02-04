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
- **Input Register**: Basic monitoring and status sensors
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
  - Remote controller room temperature
- **Performance Metrics**:
  - Flow rate
  - Heat pump power consumption
- **System Status**:
  - DHW and space heating/cooling operation
  - Various setpoints and valve positions
  - Pump speeds and PWM values
  - Disinfection and demand response modes

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

### Select Entities (Holding Register)
- **Operation Mode**: System operation mode selection with enum options

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

**Compatible Sensors:**
- Home Assistant energy monitoring sensors (e.g., from smart plugs, energy meters)
- Modbus power sensors from your electrical system
- Any sensor providing power measurements in **Watts (W)**

**How to Use:**
1. Enter the full entity ID of your power sensor (e.g., `sensor.shelly_em_power`, `sensor.modbus_electric_power`)
2. The sensor must provide power readings in Watts
3. The integration will automatically use this data for enhanced calculations

**Benefits:**
- More accurate CoP calculations
- Real-time energy efficiency monitoring
- Better understanding of system performance
- Integration with Home Assistant Energy dashboard

### Options Flow
After installation, you can configure the external electric power sensor through:
1. **Settings** → **Devices & Services**
2. Find your Daikin Altherma 4 Modbus integration
3. Click **Configure** to access options
4. Add or modify the external power sensor entity ID

## Register Support

This integration supports the following Modbus register types:

- **Input Registers (Read-only)**: Monitoring and status values
- **Binary Sensors**: Status and error detection (Input and Discrete Input)
- **Coil Registers (Writeable)**: ON/OFF control functions
- **Holding Registers (Writeable)**: Configurable setpoints and parameters
- **Climate Entities**: Advanced thermostat control
- **Number Entities**: Precise numerical control
- **Select Entities**: Enum-based selection controls

## Troubleshooting

### Common Issues
- **Connection Failed**: Verify IP address and port
- **No Data**: Check Modbus TCP settings on your heat pump
- **Update Errors**: Ensure scan interval is appropriate (minimum 10 seconds)
- **Translation Issues**: Ensure proper language settings in Home Assistant

### Debug Mode
Enable debug logging in your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ha_daikin_altherma4_modbus: debug
```

## Supported Devices

- Daikin Altherma 4 (EPSX series)
- Modbus TCP communication protocol
- Tested with firmware versions 2.2.0

## Version History

### Version 0.4.0
- Enhanced multilingual support (English/German)
- Improved device organization (Enhanced category)
- Optimized binary sensor device classes
- Fixed translation key support across all entities
- Updated thermostat placement under Enhanced category
- Comprehensive translation corrections

### Version 0.3.0
- External Electric Power Sensor integration
- Options Flow for post-installation configuration
- Signed 16-bit integer handling
- Enhanced power calculations

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the GPL-3.0-or-later License. See the [LICENSE](LICENSE) file for details.

## Credits

- Based on Daikin Altherma HT Modbus documentation
- Built with Home Assistant custom integration framework
- Uses pymodbus library for Modbus TCP communication
- Multilingual support with comprehensive translations
