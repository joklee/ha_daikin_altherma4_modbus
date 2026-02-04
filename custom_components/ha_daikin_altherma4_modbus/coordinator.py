import asyncio
import logging
from datetime import timedelta, datetime
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .const import (
    DOMAIN,
    INPUT_REGISTERS,
    HOLDING_REGISTERS,
    SELECT_REGISTERS,
    DISCRETE_INPUT_SENSORS,
    COIL_SENSORS,
    BINARY_SENSORS,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

class DaikinAlthermaCoordinator(DataUpdateCoordinator):
    """Koordinator für alle Register."""

    def __init__(self, hass, host: str, port: int, scan_interval: int = 10, demo_mode: bool = False):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self.demo_mode = demo_mode
        self.client: AsyncModbusTcpClient | None = None
        self.data = {}
        self.previous_data = {}
        self.last_triggered = {}

    async def _async_update_data(self):
        """Lese alle Register blockweise."""
        if self.demo_mode:
            _LOGGER.debug("Demo mode active - generating dummy data")
            return self._generate_demo_data()
        
        if self.client is None:
            _LOGGER.debug(f"Creating new Modbus TCP client for {self.host}:{self.port}")
            self.client = AsyncModbusTcpClient(self.host, port=self.port)
            _LOGGER.debug(f"Connecting to Modbus TCP server at {self.host}:{self.port}")
            
            try:
                await self.client.connect()
                await asyncio.sleep(0.1)
                if not self.client.connected:
                    _LOGGER.error(f"Modbus connection failed to {self.host}:{self.port}")
                    raise UpdateFailed(f"Modbus Verbindung zu {self.host}:{self.port} fehlgeschlagen")
                else:
                    _LOGGER.debug(f"Successfully connected to Modbus TCP server at {self.host}:{self.port}")
            except Exception as e:
                _LOGGER.error(f"Exception during Modbus connection to {self.host}:{self.port}: {e}")
                raise UpdateFailed(f"Modbus Verbindung zu {self.host}:{self.port} fehlgeschlagen: {e}")
        else:
            # Check if existing client is still connected
            if not self.client.connected:
                _LOGGER.warning(f"Modbus client disconnected, attempting reconnection to {self.host}:{self.port}")
                try:
                    await self.client.connect()
                    await asyncio.sleep(0.1)
                    if not self.client.connected:
                        _LOGGER.error(f"Modbus reconnection failed to {self.host}:{self.port}")
                        raise UpdateFailed(f"Modbus Verbindung zu {self.host}:{self.port} fehlgeschlagen")
                    else:
                        _LOGGER.debug(f"Successfully reconnected to Modbus TCP server at {self.host}:{self.port}")
                except Exception as e:
                    _LOGGER.error(f"Exception during Modbus reconnection to {self.host}:{self.port}: {e}")
                    raise UpdateFailed(f"Modbus Verbindung zu {self.host}:{self.port} fehlgeschlagen: {e}")

        # Adressen sammeln und 1-basiert zu 0-basiert konvertieren
        addresses = [item["address"] - 1 for item in INPUT_REGISTERS]
        start = 0
        end = max(addresses)
        count = end - start + 1

        try:
            rr = await self.client.read_input_registers(address=start, count=count)
            if rr.isError():
                raise UpdateFailed(f"Modbus Error beim Lesen der Register {start}-{end}")

            # Werte ins Dictionary schreiben
            data = {}
            
            # INPUT_REGISTERS verarbeiten
            for item in INPUT_REGISTERS:
                address = item["address"] - 1  # 1-basierte zu 0-basierten Adressen konvertieren
                reg_count = item.get("count", 1)
                dtype = item.get("dtype", "uint16")
                scale = item.get("scale", 1)
                input_type = item.get("input_type", "input")
                unique_id = item.get("unique_id", f"{address}")
                
                if reg_count == 1:
                    raw_value = rr.registers[address - start]
                    # Entity nicht erstellen wenn Wert 32766 (Kein Fehler/Normalzustand)
                    if raw_value == 32766:
                        _LOGGER.debug(f"Register {address + 1} hat Wert 32766, wird übersprungen")
                        continue
                    data[unique_id] = {
                        "value": raw_value,
                        "input_type": input_type,
                        "address": address
                    }
                else:
                    raw_value = rr.registers[address - start : address - start + reg_count]
                    # Entity nicht erstellen wenn Wert 32766 (Kein Fehler/Normalzustand)
                    if raw_value and raw_value[0] == 32766:
                        _LOGGER.debug(f"Register {address + 1} hat Wert 32766, wird übersprungen")
                        continue
                    data[unique_id] = {
                        "value": raw_value,
                        "input_type": input_type,
                        "address": address
                    }

            # DISCRETE_INPUT_SENSORS verarbeiten (mit separatem Modbus-Aufruf)
            if DISCRETE_INPUT_SENSORS:
                try:
                    # Discrete Inputs mit Function Code 2 lesen
                    discrete_addresses = [item["address"] - 1 for item in DISCRETE_INPUT_SENSORS]  # 1-basiert zu 0-basiert
                    discrete_start = min(discrete_addresses)
                    discrete_end = max(discrete_addresses)
                    discrete_count = discrete_end - discrete_start + 1
                    
                    di = await self.client.read_discrete_inputs(address=discrete_start, count=discrete_count)
                    if not di.isError():
                        for item in DISCRETE_INPUT_SENSORS:
                            address = item["address"] - 1  # 1-basiert zu 0-basiert
                            input_type = item.get("input_type", "discrete_input")
                            unique_id = item.get("unique_id", f"discrete_{address}")
                            
                            # Discrete Inputs sind 0-basiert im Array
                            if address - discrete_start < len(di.bits):
                                raw_value = 1 if di.bits[address - discrete_start] else 0
                                data[unique_id] = {
                                    "value": raw_value,
                                    "input_type": input_type,
                                    "address": address + 1  # Original 1-basierte Adresse für Logging
                                }
                            else:
                                _LOGGER.warning(f"Discrete Input {address + 1} nicht im gelesenen Bereich ({len(di.bits)} Bits)")
                    else:
                        _LOGGER.error(f"Discrete Input-Lesen fehlgeschlagen")
                except Exception as e:
                    _LOGGER.warning(f"Konnte Discrete Inputs nicht lesen: {e}")

            # COIL_SENSORS verarbeiten (mit separatem Modbus-Aufruf)
            if COIL_SENSORS:
                try:
                    # Coils mit Function Code 1 lesen
                    coil_addresses = [item["address"] - 1 for item in COIL_SENSORS]  # 1-basiert zu 0-basiert
                    coil_start = min(coil_addresses)
                    coil_end = max(coil_addresses)
                    coil_count = coil_end - coil_start + 1
                    
                    cr = await self.client.read_coils(address=coil_start, count=coil_count)
                    if not cr.isError():
                        for item in COIL_SENSORS:
                            address = item["address"] - 1  # 1-basiert zu 0-basiert
                            input_type = item.get("input_type", "coil")
                            unique_id = item.get("unique_id", f"coil_{address}")
                            
                            # Coils sind 0-basiert im Array
                            if address - coil_start < len(cr.bits):
                                raw_value = 1 if cr.bits[address - coil_start] else 0
                                data[unique_id] = {
                                    "value": raw_value,
                                    "input_type": input_type,
                                    "address": address + 1  # Original 1-basierte Adresse für Logging
                                }
                            else:
                                _LOGGER.warning(f"Coil {address + 1} nicht im gelesenen Bereich ({len(cr.bits)} Bits)")
                    else:
                        _LOGGER.error(f"Coil-Lesen fehlgeschlagen")
                except Exception as e:
                    _LOGGER.warning(f"Konnte Coils nicht lesen: {e}")
            
            # HOLDING_REGISTERS und SELECT_REGISTERS verarbeiten (wenn vorhanden)
            all_holding_registers = []
            if HOLDING_REGISTERS:
                all_holding_registers.extend(HOLDING_REGISTERS)
            if SELECT_REGISTERS:
                all_holding_registers.extend(SELECT_REGISTERS)
            
            if all_holding_registers:
                try:
                    hr = await self.client.read_holding_registers(address=0, count=79)
                    if not hr.isError():
                        for item in all_holding_registers:
                            address = item["address"] - 1  # 1-basiert zu 0-basiert
                            input_type = item.get("input_type", "holding")
                            unique_id = item.get("unique_id", f"holding_{address}")
                            
                            if address < len(hr.registers):
                                raw_value = hr.registers[address]
                                # Entity nicht erstellen wenn Wert 32766 (Kein Fehler/Normalzustand)
                                if raw_value == 32766:
                                    _LOGGER.debug(f"Holding-Register {address + 1} hat Wert 32766, wird übersprungen")
                                    continue
                                data[unique_id] = {
                                    "value": raw_value,
                                    "input_type": input_type,
                                    "address": address + 1  # Original 1-basierte Adresse für Logging
                                }
                            else:
                                _LOGGER.warning(f"Holding-Register {address + 1} nicht im gelesenen Bereich ({len(hr.registers)} Register)")
                    else:
                        _LOGGER.error(f"Holding-Register-Lesen fehlgeschlagen, nutze Input-Register als Fallback")
                except Exception as e:
                    _LOGGER.warning(f"Konnte Holding-Register nicht lesen: {e}")
                    # Fallback bei Exception
                    for item in all_holding_registers:
                        address = item["address"] - 1  # 1-basiert zu 0-basiert
                        input_type = item.get("input_type", "holding")
                        unique_id = item.get("unique_id", f"holding_{address}")
                        
                        if address <= end and address >= start:
                            raw_value = rr.registers[address - start]
                            # Entity nicht erstellen wenn Wert 32766 (Kein Fehler/Normalzustand)
                            if raw_value == 32766:
                                _LOGGER.debug(f"Holding-Register {address + 1} hat Wert 32766, wird übersprungen (Fallback)")
                                continue
                            _LOGGER.debug(f"Holding-Register {address + 1} als Input-Register gelesen (Exception): Wert {raw_value} -> {unique_id}")
                            data[unique_id] = {
                                "value": raw_value,
                                "input_type": input_type,
                                "address": address + 1  # Original 1-basierte Adresse für Logging
                            }
            
            # BINARY_SENSORS verarbeiten (überschreibt keine INPUT_REGISTERS)
            for item in BINARY_SENSORS:
                address = item["address"] - 1  # 1-basiert zu 0-basiert
                input_type = item.get("input_type", "input")
                unique_id = item.get("unique_id", f"binary_{address}")
                
                if unique_id not in data:  # Nur wenn nicht schon vorhanden
                    raw_value = rr.registers[address - start]
                    # Entity nicht erstellen wenn Wert 32766 (Kein Fehler/Normalzustand)
                    if raw_value == 32766:
                        _LOGGER.debug(f"Binary-Sensor {address + 1} hat Wert 32766, wird übersprungen")
                        continue
                    data[unique_id] = {
                        "value": raw_value,
                        "input_type": input_type,
                        "address": address + 1  # Original 1-basierte Adresse für Logging
                    }

            self.data = data

            # Track last triggered for binary sensors
            for binary in BINARY_SENSORS:
                unique_id = binary.get("unique_id", f"binary_{binary['address']}")
                current_data = data.get(unique_id, {})
                current_val = current_data.get("value")
                previous_data = self.previous_data.get(unique_id, {})
                previous_val = previous_data.get("value") if previous_data else None
                device_class = binary.get("device_class")

                if device_class == "running":
                    is_on = current_val == 0
                    was_on = previous_val == 0 if previous_val is not None else False
                    if is_on and not was_on:
                        self.last_triggered[binary["address"]] = dt_util.now()
                elif device_class == "problem":
                    is_on = current_val == 1
                    was_on = previous_val == 1 if previous_val is not None else False
                    if is_on and not was_on:
                        self.last_triggered[binary["address"]] = dt_util.now()

                # Add to data
                if binary["address"] in self.last_triggered:
                    data[f"last_triggered_{binary['address']}"] = self.last_triggered[binary["address"]]

            self.previous_data = data.copy()
            return self.data

        except ModbusException as err:
            raise UpdateFailed(f"Modbus Exception: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Lesen der Input-Register: {err}") from err

    def _generate_demo_data(self):
        """Generiere Demo-Daten für alle Sensoren."""
        import random
        from datetime import datetime, timedelta
        
        data = {}
        
        # Demo-Daten für INPUT_REGISTERS
        for item in INPUT_REGISTERS:
            address = item["address"]
            unique_id = item.get("unique_id", f"{DOMAIN}_input_{address}")
            scale = item.get("scale", 1)
            dtype = item.get("dtype", "uint16")
            
            # Realistische Demo-Werte basierend auf dem Sensortyp
            if "temperature" in item.get("name", "").lower():
                # Temperaturen zwischen 15°C und 45°C
                raw_value = random.randint(1500, 4500) if scale == 0.01 else random.randint(15, 45)
            elif "pressure" in item.get("name", "").lower():
                # Druck zwischen 1 und 10 bar
                raw_value = random.randint(100, 1000) if scale == 0.01 else random.randint(1, 10)
            elif "flow" in item.get("name", "").lower():
                # Durchfluss zwischen 5 und 25 L/min
                raw_value = random.randint(500, 2500) if scale == 0.01 else random.randint(5, 25)
            elif "power" in item.get("name", "").lower():
                # Leistung zwischen 100 und 3000 W
                raw_value = random.randint(100, 3000) if scale == 1 else random.randint(10, 300)
            elif address == 21:  # Unit abnormality
                raw_value = 0  # Kein Fehler
            elif address == 22:  # Unit abnormality code
                raw_value = 0  # Kein Fehlercode
            elif address == 40:  # Leaving water temperature PHE (benötigt für berechnete Sensoren)
                raw_value = 32
            elif address == 42:  # Return water temperature (benötigt für berechnete Sensoren)
                raw_value = 29
            elif address == 49:  # Flow rate (benötigt für berechnete Sensoren)
                raw_value = random.randint(1000, 2800)  # 10-20 L/min
            elif address == 51:  # Heat pump power consumption (benötigt für CoP)
                raw_value = random.randint(200, 800)  # 200-800 W
            else:
                # Zufällige Werte für andere Sensoren
                if dtype == "int16":
                    raw_value = random.randint(-1000, 1000)
                else:
                    raw_value = random.randint(0, 1000)
            
            data[unique_id] = {
                "value": raw_value,
                "input_type": "input",
                "address": address
            }
        
        # Demo-Daten für HOLDING_REGISTERS
        for item in HOLDING_REGISTERS:
            address = item["address"]
            unique_id = item.get("unique_id", f"{DOMAIN}_holding_{address}")
            
            # Realistische Demo-Werte für Holding-Register
            if address == 2:  # Operation mode - Select Entity
                raw_value = random.choice([0, 1, 2])  # Auto, Heating, Cooling
            elif address == 3:  # Space heating/cooling - Select Entity
                raw_value = random.choice([0, 1])  # OFF, ON
            elif address == 9:  # Quiet mode operation - Select Entity
                raw_value = random.choice([0, 1, 2])  # Off, On (Automatic), On (Manual)
            elif address == 13:  # DHW booster mode - Select Entity
                raw_value = random.choice([0, 1])  # Off, On (Powerful)
            elif address == 15:  # DHW Single heat-up - Select Entity
                raw_value = random.choice([0, 1])  # Off, On
            elif address == 67:  # Weather-dependent mode - Select Entity
                raw_value = random.choice([0, 1])  # Fixed, Weather dependent
            elif "mode" in item.get("name", "").lower():
                raw_value = random.choice([0, 1, 2, 3])  # Verschiedene Modi
            elif "setpoint" in item.get("name", "").lower():
                raw_value = random.randint(2000, 3500)  # 20-35°C
            else:
                raw_value = random.randint(0, 100)
            
            data[unique_id] = {
                "value": raw_value,
                "input_type": "holding",
                "address": address
            }
        
        # Demo-Daten für DISCRETE_INPUT_SENSORS
        for item in DISCRETE_INPUT_SENSORS:
            address = item["address"]
            unique_id = item.get("unique_id", f"{DOMAIN}_discrete_{address}")
            
            # Zufällige Binärwerte
            raw_value = random.choice([0, 1])
            
            data[unique_id] = {
                "value": raw_value,
                "input_type": "discrete_input",
                "address": address
            }
        
        # Demo-Daten für BINARY_SENSORS mit last_triggered
        for item in BINARY_SENSORS:
            address = item["address"]
            unique_id = item.get("unique_id", f"{DOMAIN}_binary_{address}")
            device_class = item.get("device_class")
            
            # Zufällige Binärwerte
            raw_value = random.choice([0, 1])
            
            data[unique_id] = {
                "value": raw_value,
                "input_type": "binary",
                "address": address
            }
            
            # Simuliere last_triggered für running/problem Sensoren
            if device_class in ["running", "problem"] and raw_value == 1:
                # Zufälliger Zeitstempel in den letzten 24 Stunden
                hours_ago = random.uniform(0, 24)
                trigger_time = dt_util.now() - timedelta(hours=hours_ago)
                self.last_triggered[address] = trigger_time
                data[f"last_triggered_{address}"] = trigger_time
        
        self.previous_data = data.copy()
        return data
