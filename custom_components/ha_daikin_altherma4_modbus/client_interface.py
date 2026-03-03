"""Abstract interface for Modbus clients."""

from abc import ABC, abstractmethod
from typing import List, Any


class ModbusClientInterface(ABC):
    """Abstract interface for Modbus clients."""
    
    @property
    @abstractmethod
    def connected(self) -> bool:
        """Check if client is connected."""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to Modbus server."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from Modbus server."""
        pass
    
    @abstractmethod
    async def read_input_registers(self, address: int, count: int) -> Any:
        """Read input registers."""
        pass
    
    @abstractmethod
    async def read_holding_registers(self, address: int, count: int) -> Any:
        """Read holding registers."""
        pass
    
    @abstractmethod
    async def read_discrete_inputs(self, address: int, count: int) -> Any:
        """Read discrete inputs."""
        pass
    
    @abstractmethod
    async def read_coils(self, address: int, count: int) -> Any:
        """Read coils."""
        pass
    
    @abstractmethod
    async def write_holding_register(self, address: int, value: int) -> Any:
        """Write to a holding register."""
        pass
    
    @abstractmethod
    async def write_coil_register(self, address: int, value: bool) -> Any:
        """Write to a coil."""
        pass
