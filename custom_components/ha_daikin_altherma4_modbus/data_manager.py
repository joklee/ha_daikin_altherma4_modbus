"""Facade data manager composed of transport/session, repository and mapping layers."""

import asyncio
import logging
import time
from typing import Any

from .const import (
    INPUT_REGISTERS,
    HOLDING_REGISTERS,
    SELECT_REGISTERS,
    HOLDING_SWITCHES,
    DISCRETE_INPUT_SENSORS,
    COIL_SENSORS,
)
from .mapping_transform import ModbusMappingTransform
from .register_repository import ModbusRegisterRepository
from .transport_session import ModbusTransportSession

_LOGGER = logging.getLogger(__name__)


class ModbusDataManager:
    """Compatibility facade orchestrating the three data layers."""

    def __init__(self, host: str, port: int, demo_mode: bool = False):
        self.host = host
        self.port = port
        self.demo_mode = demo_mode

        self._session = ModbusTransportSession(host, port, demo_mode)
        self._repository = ModbusRegisterRepository(self._session)
        self._mapping = ModbusMappingTransform()

        # Keep legacy public state references for compatibility.
        self.previous_data = self._mapping.previous_data
        self.last_triggered = self._mapping.last_triggered
        self._client_initialized = False
        self.coordinator = None

    @property
    def client(self):
        """Expose session client for existing shutdown logic."""
        return self._session.client

    @client.setter
    def client(self, value):
        self._session.client = value

    @staticmethod
    def _is_modbus_error(response) -> object | bool:
        """Compatibility shim for legacy call sites."""
        return ModbusTransportSession.is_modbus_error(response)

    async def _ensure_connection_and_prepare_data(self) -> dict:
        """Ensure active connection and keep legacy return contract."""
        await self._session.ensure_connection()
        return {}

    def _update_coordinator_data(self, register_name: str, value: Any) -> None:
        """Update coordinator data after successful write operation."""
        if self.coordinator and register_name in self.coordinator.data:
            self.coordinator.data.get(register_name, {})["value"] = value
            self.coordinator.data.get(register_name, {})["last_updated"] = time.time()
            if hasattr(self.coordinator, "async_set_updated_data"):
                try:
                    self.coordinator.async_set_updated_data(
                        self.coordinator.data.copy()
                    )
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to notify coordinator of data change: %s", err
                    )

    async def fetch_input_registers_data(self) -> dict:
        """Fetch only input registers."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_input_registers())
        else:
            _LOGGER.warning(
                "Skipping input registers fetch - no Modbus connection available"
            )

        self.previous_data.update(data)
        _LOGGER.debug("Input Registers processed in %.3fs", time.time() - start_time)
        return data

    async def fetch_discrete_inputs_data(self) -> dict:
        """Fetch only discrete inputs."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_discrete_inputs())
        else:
            _LOGGER.warning(
                "Skipping discrete inputs fetch - no Modbus connection available"
            )

        self._update_last_triggered(data)
        self.previous_data.update(data)
        _LOGGER.debug("Discrete Inputs processed in %.3fs", time.time() - start_time)
        return data

    async def fetch_coils_data(self) -> dict:
        """Fetch only coils."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_coils())
        else:
            _LOGGER.warning("Skipping coils fetch - no Modbus connection available")

        self.previous_data.update(data)
        _LOGGER.debug("Coils processed in %.3fs", time.time() - start_time)
        return data

    async def fetch_holding_registers_data(self) -> dict:
        """Fetch only holding registers."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_holding_data())
        else:
            _LOGGER.warning(
                "Skipping holding registers fetch - no Modbus connection available"
            )

        self.previous_data.update(data)
        _LOGGER.debug("Holding Registers processed in %.3fs", time.time() - start_time)
        return data

    async def refresh_holding_registers(self) -> dict:
        """Refresh holding registers for interval updates."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_holding_data())
            _LOGGER.debug("Holding Registers refresh: %.3fs", time.time() - start_time)
        else:
            _LOGGER.warning(
                "Skipping holding registers refresh - no Modbus connection available"
            )

        return data

    async def refresh_coils(self) -> dict:
        """Refresh coils for interval updates."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_coils())
            _LOGGER.debug("Coils Refresh: %.3fs", time.time() - start_time)
        else:
            _LOGGER.warning("Skipping coils refresh - no Modbus connection available")

        return data

    async def refresh_all_data(self) -> dict:
        """Refresh all Modbus data for interval updates."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_all_register_data())
            _LOGGER.debug(
                "Register refresh: Input + Discrete + Coils + Holding = %.3fs",
                time.time() - start_time,
            )
        else:
            _LOGGER.warning(
                "Skipping register refresh - no Modbus connection available"
            )

        return data

    async def fetch_all_data(self) -> dict:
        """Fetch all Modbus data and return structured data dictionary."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_all_register_data())
        else:
            _LOGGER.warning(
                "Skipping all register fetches - no Modbus connection available"
            )

        self._update_last_triggered(data)
        self.previous_data.update(data)
        _LOGGER.debug("All registers read in %.3fs", time.time() - start_time)
        return data

    async def _fetch_all_register_data(self) -> dict:
        """Common method to fetch all register groups."""
        data = {}
        data.update(await self._fetch_input_registers())
        await asyncio.sleep(0.1)
        data.update(await self._fetch_discrete_inputs())
        await asyncio.sleep(0.1)
        data.update(await self._fetch_coils())
        await asyncio.sleep(0.1)
        data.update(await self._fetch_holding_data())
        return data

    async def _fetch_input_registers(self) -> dict:
        """Fetch all input registers in configured blocks."""
        start_time = time.time()
        data = {}

        for (
            result,
            min_addr,
            max_addr,
            offset,
        ) in await self._repository.read_input_blocks():
            data.update(
                self._mapping.process_input_register_block(
                    result, INPUT_REGISTERS, min_addr, max_addr, offset
                )
            )

        _LOGGER.debug("Input Registers fully read in %.3fs", time.time() - start_time)
        return data

    async def _fetch_discrete_inputs(self) -> dict:
        """Fetch all discrete inputs."""
        start_time = time.time()
        data = {}

        result = await self._repository.read_discrete_inputs()
        if result is not None:
            data.update(
                self._mapping.process_bit_sensors(
                    result, DISCRETE_INPUT_SENSORS, "discrete_input"
                )
            )

        _LOGGER.debug("Discrete Inputs fully read in %.3fs", time.time() - start_time)
        return data

    async def _fetch_coils(self) -> dict:
        """Fetch all coils."""
        start_time = time.time()
        data = {}

        result = await self._repository.read_coils()
        if result is not None:
            data.update(self._mapping.process_bit_sensors(result, COIL_SENSORS, "coil"))

        _LOGGER.debug("Coils fully read in %.3fs", time.time() - start_time)
        return data

    async def _fetch_holding_data(self) -> dict:
        """Fetch all holding/select/switch registers in configured blocks."""
        start_time = time.time()
        data = {}
        all_holding_registers = HOLDING_REGISTERS + SELECT_REGISTERS + HOLDING_SWITCHES

        for (
            result,
            min_addr,
            max_addr,
            offset,
        ) in await self._repository.read_holding_blocks():
            data.update(
                self._mapping.process_holding_register_block(
                    result, all_holding_registers, min_addr, max_addr, offset
                )
            )

        _LOGGER.debug("Holding Registers fully read in %.3fs", time.time() - start_time)
        return data

    async def write_holding_register(self, register_name: str, value: int) -> Any:
        """Write to a holding register by register name."""
        result = await self._repository.write_holding_register(register_name, value)
        if result is not None:
            self._update_coordinator_data(register_name, value)
        return result

    async def write_coil_register(self, register_name: str, value: bool) -> Any:
        """Write to a coil register by register name."""
        result = await self._repository.write_coil_register(register_name, value)
        if result is not None:
            self._update_coordinator_data(register_name, value)
        return result

    async def _refresh_single_holding_register(
        self, register_id: str, address: int
    ) -> dict:
        """Refresh a single holding register."""
        result = await self._repository.read_single_holding_register(address)
        if result is None:
            return {}

        raw_value = result.registers[address] if len(result.registers) > address else 0
        _LOGGER.debug("Refreshed holding register %s: %s", register_id, raw_value)
        return {
            register_id: {
                "value": raw_value,
                "input_type": "holding",
                "address": address,
            }
        }

    async def _refresh_single_coil(self, register_id: str, address: int) -> dict:
        """Refresh a single coil."""
        result = await self._repository.read_single_coil(address)
        if result is None:
            return {}

        raw_value = 1 if result.bits[0] else 0
        _LOGGER.debug("Refreshed coil %s: %s", register_id, raw_value)
        return {
            register_id: {"value": raw_value, "input_type": "coil", "address": address}
        }

    def _update_last_triggered(self, data: dict):
        """Update last-triggered calculated sensors."""
        self._mapping.update_last_triggered(data)
