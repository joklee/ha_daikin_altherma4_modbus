import asyncio
import logging
from datetime import timedelta, datetime
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .const import INPUT_REGISTERS, DOMAIN, BINARY_SENSORS, HOLDING_REGISTERS, SELECT_REGISTERS

_LOGGER = logging.getLogger(__name__)

class DaikinAlthermaCoordinator(DataUpdateCoordinator):
    """Koordinator für alle Input-Register."""

    def __init__(self, hass, host: str, port: int, scan_interval: int = 10):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self.client: AsyncModbusTcpClient | None = None
        self.data = {}
        self.previous_data = {}
        self.last_triggered = {}

    async def _async_update_data(self):
        """Lese alle Input-Register blockweise."""
        if self.client is None:
            self.client = AsyncModbusTcpClient(self.host, port=self.port)
            await self.client.connect()
            await asyncio.sleep(0.1)
            if not self.client.connected:
                raise UpdateFailed(f"Modbus Verbindung zu {self.host}:{self.port} fehlgeschlagen")

        # Adressen sammeln
        addresses = [item["address"] for item in INPUT_REGISTERS]
        start = min(addresses)
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
                address = item["address"]
                reg_count = item.get("count", 1)
                dtype = item.get("dtype", "uint16")
                scale = item.get("scale", 1)
                input_type = item.get("input_type", "input")
                unique_id = item.get("unique_id", f"{address}")

                if reg_count == 1:
                    raw_value = rr.registers[address - start]
                    data[unique_id] = {
                        "value": raw_value,
                        "input_type": input_type,
                        "address": address
                    }
                else:
                    raw_value = rr.registers[address - start : address - start + reg_count]
                    data[unique_id] = {
                        "value": raw_value,
                        "input_type": input_type,
                        "address": address
                    }
            
            # HOLDING_REGISTERS und SELECT_REGISTERS verarbeiten (wenn vorhanden)
            all_holding_registers = []
            if HOLDING_REGISTERS:
                all_holding_registers.extend(HOLDING_REGISTERS)
            if SELECT_REGISTERS:
                all_holding_registers.extend(SELECT_REGISTERS)
            
            if all_holding_registers:
                _LOGGER.info(f"Verarbeite {len(all_holding_registers)} Holding-Register")
                try:
                    hr = await self.client.read_holding_registers(address=0, count=80)
                    if not hr.isError():
                        _LOGGER.info(f"Holding-Register erfolgreich gelesen: {len(hr.registers)} Register")
                        for item in all_holding_registers:
                            address = item["address"]
                            input_type = item.get("input_type", "holding")
                            unique_id = item.get("unique_id", f"holding_{address}")
                            
                            if address < len(hr.registers):
                                raw_value = hr.registers[address]
                                _LOGGER.info(f"Entry {address, input_type, unique_id, raw_value}")
                                data[unique_id] = {
                                    "value": raw_value,
                                    "input_type": input_type,
                                    "address": address
                                }
                            else:
                                _LOGGER.warning(f"Holding-Register {address} nicht im gelesenen Bereich ({len(hr.registers)} Register)")
                    else:
                        _LOGGER.error(f"Holding-Register-Lesen fehlgeschlagen, nutze Input-Register als Fallback")
                except Exception as e:
                    _LOGGER.warning(f"Konnte Holding-Register nicht lesen: {e}")
                    # Fallback bei Exception
                    for item in all_holding_registers:
                        address = item["address"]
                        input_type = item.get("input_type", "holding")
                        unique_id = item.get("unique_id", f"holding_{address}")
                        
                        if address <= end and address >= start:
                            raw_value = rr.registers[address - start]
                            _LOGGER.info(f"Holding-Register {address} als Input-Register gelesen (Exception): Wert {raw_value} -> {unique_id}")
                            data[unique_id] = {
                                "value": raw_value,
                                "input_type": input_type,
                                "address": address
                            }
            
            # BINARY_SENSORS verarbeiten (überschreibt keine INPUT_REGISTERS)
            for item in BINARY_SENSORS:
                address = item["address"]
                input_type = item.get("input_type", "input")
                unique_id = item.get("unique_id", f"binary_{address}")
                
                if unique_id not in data:  # Nur wenn nicht schon vorhanden
                    raw_value = rr.registers[address - start]
                    data[unique_id] = {
                        "value": raw_value,
                        "input_type": input_type,
                        "address": address
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
