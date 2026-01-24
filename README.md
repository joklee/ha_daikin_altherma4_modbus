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
- Unit error detection
- Circulation pump running status
- Compressor run status
- Booster heater run status
- Disinfection operation
- Defrost/Restart cycles
- Hot start detection
- Holiday mode status

### Calculated Sensors
- Heat pump power calculation
- Coefficient of Performance (CoP)
- Last triggered timestamps for key events

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
1. Copy the `daikin_altherma_modbus` folder to your `config/custom_components` directory
2. Restart Home Assistant
3. Follow steps 6-8 from HACS installation above

## Configuration

### Required Parameters
- **Connection**: Only ethernet cable
- **Host**: IP address of your Daikin heat pump
- **Port**: Modbus TCP port (default: 502)
- **Scan Interval**: Update frequency in seconds (default: 15)

### Optional Parameters
- **Electric Power Sensor**: Reference sensor for power calculations

## Register Support

This integration supports the following Modbus register types:

- **Input Registers (Read-only)**: Monitoring and status values
- **Binary Sensors**: Status and error detection
- **Coil Registers (Writeable)**: ON/OFF control functions
- **Holding Registers (Writeable)**: Configurable setpoints and parameters

## Troubleshooting

### Common Issues
- **Connection Failed**: Verify IP address and port
- **No Data**: Check Modbus TCP settings on your heat pump
- **Update Errors**: Ensure scan interval is appropriate (minimum 10 seconds)

### Debug Mode
Enable debug logging in your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.daikin_altherma_modbus: debug
```

## Supported Devices

- Daikin Altherma 4 (EPSX series)
- Modbus TCP communication protocol
- Tested with firmware versions 2.2.0

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the GPL-3.0-or-later License. See the [LICENSE](LICENSE) file for details.

## Credits

- Based on Daikin Altherma HT Modbus documentation
- Built with Home Assistant custom integration framework
- Uses pymodbus library for Modbus TCP communication
