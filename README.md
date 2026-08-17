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

**Short description:** This integration connects Daikin Altherma 4 heat pumps (EPSX series) to Home Assistant via Modbus TCP. It provides comprehensive monitoring of temperatures, power consumption, and operating states, as well as control of heating zones, domestic hot water, and operation modes.

**⚠️ WARNING: Use at your own risk! This integration modifies heat pump settings. Incorrect configuration may damage your equipment or void your warranty. Always consult the official Daikin documentation before making changes.**

**Note:** Not all registers may provide valid values depending on your heat pump model and configuration. Some registers might return zero, error codes, or unexpected values. Always verify values against your heat pump's display or official documentation.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Enabling Modbus TCP](#enabling-modbus-tcp)
- [Installation](#installation)
- [Configuration](#configuration)
- [Supported Features & Entities](#supported-features--entities)
- [Services](#services)
- [Use Cases](#use-cases)
- [Automation Examples](#automation-examples)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Removal](#removal)
- [Supported Devices](#supported-devices)
- [Development & Testing](#development--testing)
- [License](#license)

---

## Prerequisites

1. **Daikin Altherma 4 heat pump** (EPSX series) with Modbus TCP support
2. **MMI Version 2.2.0 or higher** (check the version on your heat pump's display)
3. **Ethernet network access** to the heat pump (WiFi is not supported)
4. **Network cable (RJ45)** connected between your heat pump and network
5. **Modbus TCP enabled** on your heat pump (see activation instructions below)
6. **Home Assistant 2024.1 or higher**

---

## Enabling Modbus TCP

Before using this integration, you need to enable Modbus TCP communication on your Daikin Altherma 4 heat pump.

### Modbus Protocol

- **Protocol:** Modbus TCP/IP
- **Network:** Ethernet only (WiFi is not supported)
- **Port without encryption:** 502
- **Port with TLS encryption:** 802 (not tested)

> **Note:** If the unit receives commands from both Modbus and Cloud interfaces, it will execute the command that was received most recently.

### Connection Limits

The heat pump supports a total of **3 concurrent connections**. Examples:
- 3× port 502
- 3× port 802
- Combination, e.g. 1× port 502 and 2× port 802

### Step-by-Step Activation

1. **Access the heat pump controller** – Navigate to the main control unit (outdoor unit or hydrobox)
2. **Enter installer mode** – Press and hold the installer button (may require installer password)
3. **Navigate to network settings** – Go to: **Settings** → **Network** → **Modbus**
4. **Enable Modbus TCP/IP** – Set Modbus TCP to **Enabled**
5. **Configure network parameters:**
   - **Port:** Set to `502` (standard Modbus TCP port)
   - **IP Address:** Note the IP address assigned to your heat pump
6. **Save settings** and exit installer mode
7. **Verify network connectivity** – Ensure the heat pump is reachable from your Home Assistant network
8. **Test the connection:** `telnet <heat-pump-ip> 502`

---

## Installation

### HACS Installation (Recommended)

1. Open Home Assistant and navigate to **HACS** → **Integrations**
2. Click the three dots menu (⋮) and select **Custom repositories**
3. Add repository URL: `https://github.com/joklee/ha_daikin_altherma4_modbus`
4. Select category: **Integration**
5. Click **Download** to install the integration
6. Restart Home Assistant
7. Go to **Settings** → **Devices & Services** → **Integrations**
8. Click **+ Add Integration** and search for "Daikin Altherma 4 Modbus"
9. Enter your heat pump's IP address and port (default: 502)
10. Complete the configuration with your preferred polling intervals

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/ha_daikin_altherma4_modbus` folder to your Home Assistant `config/custom_components` directory
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Integrations**
5. Click **+ Add Integration** and search for "Daikin Altherma 4 Modbus"
6. Enter your heat pump's IP address and port (default: 502)
7. Complete the configuration with your preferred polling intervals

### Testing Without Hardware

If you want to test the integration without a physical heat pump connected:
- Set the host address to `localhost`
- The integration will use realistic mock data
- All 50+ input registers generate realistic values
- Perfect for development and demonstration

---

## Configuration

### Required Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| **Host** | IP address of your Daikin heat pump | – |
| **Port** | Modbus TCP port | `502` |

### Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| **Scan Interval (seconds)** | Polling interval for normal registers | `10` |
| **Slow Scan Interval (seconds)** | Polling interval for slowly changing registers | `600` |
| **Electric Power Sensor** | Entity ID of an external power sensor for CoP calculation | – |
| **Demo Mode** | Skip connection test (for testing without hardware) | `false` |

### External Power Sensor

The **Electric Power Sensor** parameter allows you to integrate an external power measurement device for more accurate energy monitoring:

**Purpose:**
- Improves the calculated **Coefficient of Performance (CoP)** with real electrical power data
- Enables real-time thermal efficiency calculation
- Integrates with the Home Assistant Energy Dashboard

**Compatible Sensors:**
- **Smart Plugs:** Shelly, TP-Link Kasa, Sonoff POW
- **Energy Meters:** Modbus power sensors, DIN-rail energy meters
- **Any sensor** providing power readings in **Watts (W)**

**How to Configure:**
1. Install your power sensor (smart plug, energy meter, etc.)
2. Add it to Home Assistant (if not already done)
3. Find the entity ID in Developer Tools → States
4. Enter the full entity ID in the integration configuration
5. Make sure the sensor provides power readings in Watts

**Examples:**
```
sensor.shelly_em_power          # Shelly EM (whole house)
sensor.shelly_plug_power        # Shelly Plug (heat pump only)
sensor.modbus_electric_power    # Modbus energy meter
sensor.total_home_power         # Home Assistant Energy
```

### Changing Options

After installation, you can modify settings via:
1. **Settings** → **Devices & Services**
2. Find your Daikin Altherma 4 Modbus integration
3. Click **Configure** to edit options

### Changing Connection Details

You can change the host address and port via the reconfigure flow:
1. **Settings** → **Devices & Services** → **Daikin Altherma 4 Modbus**
2. Click **Configure**
3. Change host/port – the new connection will be tested before applying

---

## Supported Features & Entities

### Overview

| Platform | Count | Description |
|----------|-------|-------------|
| Sensor | ~50+ | Temperatures, power, status values |
| Binary Sensor | 26 | Binary status indicators (diagnostic) |
| Switch | 6 | On/Off control (coils + holding) |
| Number | 20+ | Setpoint settings |
| Select | 10+ | Operation mode selection |
| Climate | 2 | Thermostat control |

### Sensors (Input Registers)

#### Temperature Sensors
<<<<<<< HEAD
| Sensor | Address | Unit | Device Class | State Class | Description |
|--------|---------|------|-------------|------------|-------------|
| Leaving water temperature PHE | 40 | °C | temperature | measurement | Primary heat exchanger outlet |
| Leaving water temperature BUH | 41 | °C | temperature | measurement | Backup heater outlet |
| Return water temperature | 42 | °C | temperature | measurement | Water return |
| DHW temperature | 43 | °C | temperature | measurement | Domestic hot water |
| Outside air temperature | 44 | °C | temperature | measurement | Outdoor sensor |
| Liquid refrigerant temperature | 45 | °C | temperature | measurement | Refrigerant |
| Remote control room temp (Main) | 50 | °C | temperature | measurement | Thermostat reading |
| Remote control room temp (Add) | 78 | °C | temperature | measurement | Thermostat reading additional zone |
| Mixing leaving water temp | 72 | °C | temperature | measurement | Mixing kit outlet |
| Space heating/cooling target Main in mixing kit | 73 | °C | temperature | measurement | Mixing kit target temperature |
| Leaving water temp prePHE outdoor | 74 | °C | temperature | measurement | – |
| Leaving water temp Tank valve | 75 | °C | temperature | measurement | – |
| DHW Upper temperature | 76 | °C | temperature | measurement | – |
| DHW Lower temperature | 77 | °C | temperature | measurement | – |

#### Power and Flow Sensors
| Sensor | Address | Unit | Device Class | State Class | Description |
|--------|---------|------|-------------|------------|-------------|
| Flow rate | 49 | L/min | volume_flow_rate | measurement | Water flow rate |
| Heat pump power consumption | 51 | kW | power | measurement | Electrical input power |
| Water pressure | 79 | bar | pressure | measurement | – |
=======
| Sensor | Address | Unit | Description |
|--------|---------|------|-------------|
| Leaving water temperature PHE | 40 | °C | Primary heat exchanger outlet |
| Leaving water temperature BUH | 41 | °C | Backup heater outlet |
| Return water temperature | 42 | °C | Water return |
| DHW temperature | 43 | °C | Domestic hot water |
| Outside air temperature | 44 | °C | Outdoor sensor |
| Liquid refrigerant temperature | 45 | °C | Refrigerant |
| Remote control room temp (Main) | 50 | °C | Thermostat reading |
| Remote control room temp (Add) | 78 | °C | Thermostat reading additional zone |
| Mixing leaving water temp | 72 | °C | Mixing kit outlet |
| Space heating/cooling target Main in mixing kit | 73 | °C | Mixing kit target temperature |
| Leaving water temp prePHE outdoor | 74 | °C | – |
| Leaving water temp Tank valve | 75 | °C | – |
| DHW Upper temperature | 76 | °C | – |
| DHW Lower temperature | 77 | °C | – |

#### Power and Flow Sensors
| Sensor | Address | Unit | Description |
|--------|---------|------|-------------|
| Flow rate | 49 | L/min | Water flow rate |
| Heat pump power consumption | 51 | kW | Electrical input power |
| Water pressure | 79 | bar | – |
>>>>>>> 7851c25 (docs: rewrite README as home-assistant.io-conform documentation)

#### Operating Status
| Sensor | Address | Description |
|--------|---------|-------------|
| Operation mode | 38 | None/Heating/Cooling |
| 3-way valve | 37 | Heating/DHW |
| Circulation pump running | 30 | On/Off |
| Compressor run | 31 | On/Off |
| Booster heater run | 32 | On/Off |
| Disinfection operation | 33 | On/Off |
| Defrost/Restart | 35 | On/Off |
| Hot start | 36 | On/Off |
| Unit operation mode | 83 | Stop/Tank Heat Up/Heating/Cooling/Actuator |

#### Status and Control Values
| Sensor | Address | Unit | Description |
|--------|---------|------|-------------|
| Bypass valve position | 66 | % | – |
| Storage valve position | 67 | % | – |
| Circulation pump speed | 68 | % | – |
| Mixed pump PWM | 69 | % | – |
| Direct pump PWM | 70 | % | – |
| Mixing valve position | 71 | % | – |

#### Error Monitoring
| Sensor | Address | Description |
|--------|---------|-------------|
| Unit abnormality | 21 | 0=No error, 1=Fault, 2=Warning |
| Abnormality code | 22 | Text code |
| Abnormality sub code | 23 | Numeric code |
| Abnormality counter | 82 | User abnormality counter |

#### Setpoint Limits
| Sensor | Address | Unit | Description |
|--------|---------|------|-------------|
| Heating leaving water Min/Max (Main) | 54-55 | °C | – |
| Cooling leaving water Min/Max (Main) | 56-57 | °C | – |
| Heating leaving water Min/Max (Add) | 58-59 | °C | – |
| Cooling leaving water Min/Max (Add) | 60-61 | °C | – |
| Room heating Min/Max | 84-85 | °C | – |
| Room cooling Min/Max | 86-87 | °C | – |

### Binary Sensors (Discrete Inputs)

All binary sensors have the **Diagnostic** category.

| Sensor | Address | Device Class |
|--------|---------|-------------|
| Shut-off valve | 1 | running |
| Backup heater relays 1-6 | 2-7 | running |
| Booster heater | 8 | running |
| Tank boiler | 9 | running |
| Bivalent | 10 | running |
| Compressor running | 11 | running |
| Quiet mode operation active | 12 | – |
| Holiday mode active | 13 | – |
| Antifrost status | 14 | – |
| Water pipe freeze prevention | 15 | – |
| Disinfection operation | 16 | running |
| Defrost | 17 | running |
| Hot start | 18 | running |
| DHW running | 19 | running |
| Main zone running | 20 | running |
| Additional zone running | 21 | running |
| Powerful tank heat up request | 22 | – |
| Manual tank heat up request | 23 | – |
| Emergency active | 24 | problem |
| Circulation pump running | 25 | running |
| Imposed limit acceptance | 26 | – |

### Switches

#### Coil Registers (On/Off)
| Switch | Address | Description |
|--------|---------|-------------|
| Domestic Hot Water On/Off | 1 | Enable/disable DHW |
| Main zone On/Off | 2 | Enable/disable main heating zone |
| Additional zone On/Off | 3 | Enable/disable additional heating zone |

#### Holding Registers (Switchable)
| Switch | Address | Description |
|--------|---------|-------------|
| Space heating/cooling On/Off | 4 | Heating/cooling operation |
| DHW booster mode (Powerful) | 13 | DHW rapid heating |
| DHW Single heat-up (Manual) | 15 | Manual DHW one-time heat-up |

### Number Entities

| Number | Address | Unit | Min | Max | Description |
|--------|---------|------|-----|-----|-------------|
| Main Heating setpoint | 1 | °C | 0 | 100 | – |
| Main Cooling setpoint | 2 | °C | 0 | 100 | – |
| Room Heating setpoint Main | 6 | °C | 12 | 30 | – |
| Room Cooling setpoint Main | 7 | °C | 12 | 35 | – |
| DHW reheat setpoint | 10 | °C | 30 | 85 | – |
| DHW boost setpoint (Powerful) | 14 | °C | 30 | 85 | Powerful |
| DHW Single Heat-up Setpoint (Manual) | 16 | °C | 30 | 85 | Manual |
| Main LWT Heating offset | 54 | °C | -10 | +10 | Weather-dependent |
| Main LWT Cooling offset | 55 | °C | -10 | +10 | Weather-dependent |
| Imposed power limit | 58 | kW | 0 | 20 | – |
| Add Heating setpoint | 63 | °C | 3 | 85 | – |
| Add Cooling setpoint | 64 | °C | 3 | 85 | – |
| Add LWT Heating offset | 66 | °C | -10 | +10 | Weather-dependent |
| Add LWT Cooling offset | 67 | °C | -10 | +10 | Weather-dependent |
| Room Heating setpoint Main (Fine) | 76 | °C | 12 | 30 | Temp16 |
| Room Cooling setpoint Main (Fine) | 77 | °C | 12 | 35 | Temp16 |
| Room Heating setpoint Add (Fine) | 78 | °C | 12 | 30 | Temp16 |
| Room Cooling setpoint Add (Fine) | 79 | °C | 12 | 35 | Temp16 |

### Select Entities

| Select | Address | Options |
|--------|---------|---------|
| Operation mode | 3 | Auto, Heating, Cooling |
| Quiet mode | 9 | Off, Automatic, Manual |
| DHW booster | 13 | Off, Powerful |
| DHW Single Heat-up | 15 | Off, On |
| Weather-dependent Heating Main | 68 | Fixed, Weather-dependent |
| Weather-dependent Cooling Main | 69 | Fixed, Weather-dependent |
| Thermostat Request Main | 74 | None, Heating, Cooling |
| Thermostat Request Add | 75 | None, Heating, Cooling |
| DHW mode | 80 | Reheat, Schedule and reheat, Scheduled, Off |
| Smart Grid | 56 | Free, Forced off, Recommended on, Forced on |

### Climate Entities

| Climate | Description |
|---------|-------------|
| Main zone | Thermostat control for main heating zone with operation modes |
| DHW | Domestic hot water control |

### Calculated Sensors

| Sensor | Unit | Device Class | Description |
|--------|------|-------------|-------------|
| Thermal Heat Output | W | power | `Flow rate × |ΔT| × 70` |
| Coefficient of Performance | CoP | – | `Heat output / Electric power` |
| Delta-T | K | – | `Leaving water − Return water` |
| Last Compressor Run | – | timestamp | Timestamp of last compressor start |
| Last Defrost | – | timestamp | Timestamp of last defrost cycle |
| Last Booster Heater | – | timestamp | Timestamp of last auxiliary heater activation |
| Last DHW Running | – | timestamp | Timestamp of last DHW heating cycle |

### Special Register Values

| Value | Meaning | Applies to |
|-------|---------|------------|
| 32765 | Not available / in error state | Various input registers |
| 32766 | No error / not supported | Abnormality sub code, DHW mode |
| 32767 | Register not supported by device | Any input register (skipped during setup) |

When a register returns 32767 during initial setup, the corresponding sensor entity is not created.

---

## Services

The integration provides the following Home Assistant services.

**Note:** All services require the `config_entry_id` parameter (the config entry ID of your heat pump).

### Basic Control

| Service | Description | Parameter | Values |
|---------|-------------|-----------|--------|
| `set_operation_mode` | Set heat pump operation mode | `operation_mode` | `off`, `heat`, `cool` |
| `set_dhw_state` | Enable/disable DHW | `state` | `true`, `false` |
| `set_main_zone_state` | Enable/disable main heating zone | `state` | `true`, `false` |
| `set_additional_zone_state` | Enable/disable additional heating zone | `state` | `true`, `false` |
| `set_smart_grid_mode` | Set Smart Grid mode | `smart_grid_mode` | `free running`, `forced off`, `recommended on`, `forced on` |

### Advanced Control

| Service | Description | Parameter | Values |
|---------|-------------|-----------|--------|
| `set_quiet_mode` | Set quiet/night mode | `quiet_mode` | `off`, `on (automatic)`, `on (manual)` |
| `set_dhw_booster_mode` | DHW booster (Powerful) | `booster_mode` | `true`, `false` |
| `set_dhw_single_heatup` | DHW one-time heat-up | `single_heatup`, `setpoint` | `true`, `false`; 30-85°C (optional) |
| `set_power_limit` | Imposed power limit | `power_limit` | 0-20 kW |
| `set_heating_offset` | Weather-dependent heating offset | `offset` | -10 to +10 K |
| `set_cooling_offset` | Weather-dependent cooling offset | `offset` | -10 to +10 K |
| `set_room_heating_setpoint` | Room thermostat heating setpoint | `setpoint` | 12-30°C |
| `set_room_cooling_setpoint` | Room thermostat cooling setpoint | `setpoint` | 12-35°C |
| `set_additional_zone_setpoint` | Additional zone setpoint | `setpoint` | 3-85°C |
| `refresh_connection` | Refresh Modbus connection | – | – |

---

## Use Cases

### 1. Optimize Energy Costs
Use Smart Grid mode and automatic power limiting to reduce operating costs. The heat pump can automatically heat during low electricity prices and throttle during expensive peak hours.

### 2. Automate Comfort
Adjust room temperature setpoints based on occupancy, time of day, or weather forecast. Use quiet mode automatically at night or during rest periods.

### 3. Domestic Hot Water Management
Schedule DHW heating for peak times (e.g., morning before showers) and use the booster mode for rapid reheating when needed.

### 4. Monitor Energy Efficiency
Track the CoP (Coefficient of Performance) in real-time to monitor your heat pump's efficiency and detect degradation early.

### 5. Outside Temperature-Based Adjustment
Use weather-dependent offsets to automatically adjust the flow temperature based on outdoor conditions, maximizing comfort while maintaining efficiency.

### 6. Multi-Zone Control
Independently control main and additional heating zones with individual setpoints and operation modes for different building areas.

---

## Automation Examples

### Heat DHW During Low Electricity Prices

```yaml
automation:
  - alias: "Heat water when electricity is cheap"
    trigger:
      - platform: numeric_state
        entity_id: sensor.electricity_price
        below: 0.20
    action:
      - service: ha_daikin_altherma4_modbus.set_dhw_state
        data:
          config_entry_id: "abc123def456"
          state: true
```

### Smart Grid with Dynamic Pricing

```yaml
automation:
  - alias: "Smart Grid control"
    trigger:
      - platform: time_pattern
        minutes: "/30"
    action:
      - choose:
          - conditions:
              - condition: numeric_state
                entity_id: sensor.electricity_price
                below: 0.15
            sequence:
              - service: ha_daikin_altherma4_modbus.set_smart_grid_mode
                data:
                  config_entry_id: "abc123def456"
                  smart_grid_mode: "forced on"
          - conditions:
              - condition: numeric_state
                entity_id: sensor.electricity_price
                above: 0.35
            sequence:
              - service: ha_daikin_altherma4_modbus.set_smart_grid_mode
                data:
                  config_entry_id: "abc123def456"
                  smart_grid_mode: "forced off"
```

### Enable Quiet Mode at Night

```yaml
automation:
  - alias: "Night quiet mode"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: ha_daikin_altherma4_modbus.set_quiet_mode
        data:
          config_entry_id: "abc123def456"
          quiet_mode: "on (automatic)"
```

### Power Limit During Peak Hours

```yaml
automation:
  - alias: "Peak hour power limit"
    trigger:
      - platform: time_pattern
        hours: "18-20"
    action:
      - service: ha_daikin_altherma4_modbus.set_power_limit
        data:
          config_entry_id: "abc123def456"
          power_limit: 3.5
```

### Morning DHW Booster

```yaml
automation:
  - alias: "Morning DHW boost"
    trigger:
      - platform: time
        at: "06:30:00"
    action:
      - service: ha_daikin_altherma4_modbus.set_dhw_booster_mode
        data:
          config_entry_id: "abc123def456"
          booster_mode: true
```

### Room Temperature Based on Occupancy

```yaml
automation:
  - alias: "Comfort temperature when home"
    trigger:
      - platform: state
        entity_id: input_boolean.home_occupied
        to: "on"
    action:
      - service: ha_daikin_altherma4_modbus.set_room_heating_setpoint
        data:
          config_entry_id: "abc123def456"
          setpoint: 21

  - alias: "Energy-saving mode when away"
    trigger:
      - platform: state
        entity_id: input_boolean.home_occupied
        to: "off"
    action:
      - service: ha_daikin_altherma4_modbus.set_room_heating_setpoint
        data:
          config_entry_id: "abc123def456"
          setpoint: 17
```

### CoP Monitoring with Notification

```yaml
automation:
  - alias: "Low efficiency notification"
    trigger:
      - platform: numeric_state
        entity_id: sensor.daikin_altherma4_cop
        below: 2.5
        for:
          minutes: 30
    action:
      - service: notify.notify
        data:
          title: "Heat pump efficiency warning"
          message: "CoP has been below 2.5 for 30 minutes (current: {{ states('sensor.daikin_altherma4_cop') }})"
```

### Daily Connection Refresh

```yaml
automation:
  - alias: "Daily connection refresh"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: ha_daikin_altherma4_modbus.refresh_connection
        data:
          config_entry_id: "abc123def456"
```

---

## Known Limitations

1. **Ethernet only:** WiFi is not supported by the heat pump for Modbus TCP. A wired network connection is required.

2. **Max. 3 connections:** The Daikin Altherma 4 supports a maximum of 3 simultaneous Modbus connections. Other systems (e.g., Daikin Online Controller, other integrations) share this limit.

3. **Model-dependent:** Not all registers are supported by every heat pump model. Registers returning 32767 during setup are automatically skipped.

4. **No real-time control:** Modbus TCP is polling-based. The minimum polling interval is 10 seconds. This integration is not suitable for immediate reactions.

5. **Change-based algorithm:** The Modbus algorithm is change-based. The heat pump is only updated if a change is detected. To prevent changes from being lost due to communication outages, it is recommended to periodically refresh state from the client side.

6. **TLS not tested:** TLS encryption (port 802) has not been tested and is not officially supported.

7. **CoP calculation:** The automatic CoP calculation is based on internal measurements. For higher accuracy, using an external power sensor is recommended.

8. **No firmware updates:** The integration cannot provide or manage firmware updates for the heat pump.

---

## Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Connection failed | Wrong IP/port | Verify IP address and port |
| No data | Modbus TCP not enabled | Check Modbus settings on heat pump |
| Entities unavailable | Register not supported | Check heat pump model compatibility |
| Update errors | Scan interval too short | Set to at least 10 seconds |
| Performance issues | Polling too frequently | Increase scan intervals |

### Connection and Network Issues

- **Device offline:** The integration automatically attempts to reestablish the connection
- **Network interruption:** Automatic reconnection with exponential backoff (max. 30 seconds)
- **Timeout errors:** Retry logic with 2-3 attempts before reporting failure
- **Connection test:** `telnet <heat-pump-ip> 502`

### Enable Debug Logging

Add the following lines to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ha_daikin_altherma4_modbus: debug
```

### Repair Issues

The integration uses the Home Assistant Repair system:
- **Connection lost:** A repair issue is created when the connection is lost. You can fix the connection directly from the HA UI.
- **Device abnormality:** When the heat pump reports errors or warnings (register 21), an informational repair issue is created.

### Advanced Troubleshooting

1. **Validate Modbus registers:** Use demo mode (host: localhost) to test integration logic
2. **Check network:** Test connectivity with `telnet <ip> 502`
3. **Register coverage:** Check your device documentation for supported register ranges
4. **Monitor performance:** Watch Home Assistant logs for connection patterns
5. **Export data:** Use the diagnostics function (Integration → Download diagnostic data)

---

## Removal

### Remove Integration Entry

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Find your **Daikin Altherma 4 Modbus** integration entry
3. Click the three dots menu (⋮) and select **Delete**
4. Confirm the deletion

### Cleanup (Optional)

**For HACS installation:**
1. Go to **HACS** → **Integrations**
2. Find **Daikin Altherma 4 Modbus**
3. Click the three dots menu (⋮) and select **Uninstall**
4. Restart Home Assistant

**For manual installation:**
1. Remove the `custom_components/ha_daikin_altherma4_modbus` folder from your Home Assistant configuration directory
2. Restart Home Assistant

### Heat Pump Settings

Removing this integration does not modify any settings on your Daikin Altherma 4 heat pump. The heat pump will continue operating with its current configuration using its internal controls or other connected interfaces.

---

## Supported Devices

### Compatible Models

- EPBX07A, EPBX10A, EPBX14A
- EPSX07P30A, EPSX07P50A
- EPSX(B)10P30A, EPSX(B)10P50A
- EPSX10P50AF
- EPSX(B)14P30A, EPSX(B)14P50A
- EPSXB07P30A, EPSXB07P50A
- EPVX07S(U)18A, EPVX07S(U)23A
- EPVX10S(U)18A, EPVX10S(U)23A
- EPVX14S(U)18A, EPVX14S(U)23A
- EPVZ07S18A, EPVZ07S23A
- EPVZ10S18A, EPVZ10S23A
- EPVZ14S18A, EPVZ14S23A

### Technical Requirements

- Modbus TCP communication protocol
- MMI Version 2.2.0 or higher
- Ethernet connection (WiFi is not supported)
- Port 502 (unencrypted) or Port 802 (TLS)

---

## Development & Testing

### Test Suite

- **298 automated tests** covering core functionality
- **Mock client** for development without hardware
- **Coverage reports** for quality assurance
- **Integration tests** for full workflow validation
- **Performance benchmarks** for optimization

### Development Setup

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests
make test-unit

# Or directly with pytest
python -m pytest tests/ --cov=custom_components/ha_daikin_altherma4_modbus

# Full CI pipeline
make ci-local

# Code quality
make lint
make format-check

# Performance benchmarks
make benchmark
```

### Dev Features

- **Demo mode:** Built-in mock client for testing (host: `localhost`)
- **Debug logging:** Comprehensive logging for troubleshooting
- **Modular architecture:** Clean separation of concerns
- **Type hints:** Full type annotation support
- **Multilingual:** English and German translations

---

## License

This project is licensed under the GPL-3.0-or-later License. See the [LICENSE](LICENSE.TXT) file for details.

---

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Credits

- Based on Daikin Altherma HT Modbus documentation
- Built with the Home Assistant Custom Integration Framework
- Uses the pymodbus library for Modbus TCP communication
- Multilingual support with comprehensive translations