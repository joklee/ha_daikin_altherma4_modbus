"""Facade data manager composed of transport/session, repository and mapping layers."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .const import (
    COIL_REGISTERS,
    DISCRETE_INPUT_SENSORS,
    HOLDING_REGISTERS,
    HOLDING_SELECT_REGISTERS,
    HOLDING_SWITCHES,
    INPUT_REGISTERS,
)
from .data_types import StateData
from .mapping_transform import ModbusMappingTransform
from .register_repository import ModbusRegisterRepository
from .transport_session import ModbusTransportSession

_LOGGER = logging.getLogger(__name__)


@dataclass
class ModbusDataManager:
    """Compatibility facade orchestrating the three data layers."""

    host: str
    port: int
    demo_mode: bool = False

    _session: ModbusTransportSession = field(init=False)
    _repository: ModbusRegisterRepository = field(init=False)
    _mapping: ModbusMappingTransform = field(init=False)
    _client_initialized: bool = field(default=False, init=False)
    coordinator: Any = field(default=None, init=False)

    def __post_init__(self):
        """Initialize internal components after dataclass creation."""
        self._session = ModbusTransportSession(self.host, self.port, self.demo_mode)
        self._repository = ModbusRegisterRepository(self._session)
        self._mapping = ModbusMappingTransform()

        # Keep legacy public state references for compatibility.
        self.previous_data = self._mapping.previous_data
        self.last_triggered = self._mapping.last_triggered

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

    async def _ensure_connection_and_prepare_data(self) -> StateData:
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

    async def fetch_input_registers_data(self) -> StateData:
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

    async def fetch_discrete_inputs_data(self) -> StateData:
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

    async def fetch_coils_data(self) -> StateData:
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

    async def fetch_holding_registers_data(self) -> StateData:
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

    async def refresh_holding_registers(self) -> StateData:
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

    async def refresh_coils(self) -> StateData:
        """Refresh coils for interval updates."""
        start_time = time.time()
        data = await self._ensure_connection_and_prepare_data()

        if self.client is not None:
            data.update(await self._fetch_coils())
            _LOGGER.debug("Coils Refresh: %.3fs", time.time() - start_time)
        else:
            _LOGGER.warning("Skipping coils refresh - no Modbus connection available")

        return data

    async def refresh_all_data(self) -> StateData:
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

    async def fetch_all_data(self) -> StateData:
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

    async def _fetch_all_register_data(self) -> StateData:
        """Common method to fetch all register groups."""
        data = {}
        data.update(await self._fetch_input_registers())
        data.update(await self._fetch_discrete_inputs())
        data.update(await self._fetch_coils())
        data.update(await self._fetch_holding_data())
        return data

    async def _fetch_input_registers(self) -> StateData:
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

    async def _fetch_discrete_inputs(self) -> StateData:
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

    async def _fetch_coils(self) -> StateData:
        """Fetch all coils."""
        start_time = time.time()
        data = {}

        result = await self._repository.read_coils()
        if result is not None:
            data.update(
                self._mapping.process_bit_sensors(result, COIL_REGISTERS, "coil")
            )

        _LOGGER.debug("Coils fully read in %.3fs", time.time() - start_time)
        return data

    async def _fetch_holding_data(self) -> StateData:
        """Fetch all holding/select/switch registers in configured blocks."""
        start_time = time.time()
        data = {}
        all_holding_registers = (
            HOLDING_REGISTERS + HOLDING_SELECT_REGISTERS + HOLDING_SWITCHES
        )

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

    def _update_last_triggered(self, data: StateData):
        """Update last-triggered calculated sensors."""
        self._mapping.update_last_triggered(data)
