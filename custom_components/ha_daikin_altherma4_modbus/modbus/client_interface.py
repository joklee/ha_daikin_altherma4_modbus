"""Abstract interface for Modbus clients."""

from abc import ABC, abstractmethod
from typing import Any


class ModbusClientInterface(ABC):
    """Abstract interface for Modbus clients."""

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Check if client is connected."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to Modbus server."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from Modbus server."""

    @abstractmethod
    async def read_input_registers(self, address: int, count: int) -> Any:
        """Read input registers."""

    @abstractmethod
    async def read_holding_registers(self, address: int, count: int) -> Any:
        """Read holding registers."""

    @abstractmethod
    async def read_discrete_inputs(self, address: int, count: int) -> Any:
        """Read discrete inputs."""

    @abstractmethod
    async def read_coils(self, address: int, count: int) -> Any:
        """Read coils."""

    @abstractmethod
    async def write_holding_register(self, address: int, value: int) -> Any:
        """Write to a holding register."""

    @abstractmethod
    async def write_coil_register(self, address: int, value: bool) -> Any:
        """Write to a coil."""
