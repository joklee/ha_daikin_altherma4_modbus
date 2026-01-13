import asyncio
import logging
from datetime import timedelta, datetime
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .const import INPUT_REGISTERS, DOMAIN, BINARY_SENSORS

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
            for item in INPUT_REGISTERS + BINARY_SENSORS:
                address = item["address"]
                reg_count = item.get("count", 1)
                dtype = item.get("dtype", "uint16")
                scale = item.get("scale", 1)

                if reg_count == 1:
                    data[address] = rr.registers[address - start]
                else:
                    data[address] = rr.registers[address - start : address - start + reg_count]

            self.data = data

            # Track last triggered for binary sensors
            for binary in BINARY_SENSORS:
                address = binary["address"]
                current_val = data.get(address)
                previous_val = self.previous_data.get(address)
                device_class = binary.get("device_class")

                if device_class == "running":
                    is_on = current_val == 0
                    was_on = previous_val == 0 if previous_val is not None else False
                    if is_on and not was_on:
                        self.last_triggered[address] = dt_util.now()
                elif device_class == "problem":
                    is_on = current_val == 1
                    was_on = previous_val == 1 if previous_val is not None else False
                    if is_on and not was_on:
                        self.last_triggered[address] = dt_util.now()

                # Add to data
                if address in self.last_triggered:
                    data[f"last_triggered_{address}"] = self.last_triggered[address]

            self.previous_data = data.copy()
            return self.data

        except ModbusException as err:
            raise UpdateFailed(f"Modbus Exception: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Lesen der Input-Register: {err}") from err
