"""Register definition dataclasses for type-safe Modbus register handling."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Union

from homeassistant.const import EntityCategory


@dataclass
class RegisterDefinition:
    """Base class for all register definitions."""

    name: str
    address: int
    input_type: str
    register_name: str
    calc_type: Optional[str] = None  # For calculated registers
    trigger_register_name: Optional[str] = None  # For calculated registers

    # Optional fields with defaults
    unit: Optional[str] = None
    device_class: Optional[str] = None
    icon: Optional[str] = None
    translation_key: Optional[str] = None
    entity_category: Optional[EntityCategory] = None


@dataclass
class SensorRegister(RegisterDefinition):
    """Register definition for sensor entities."""

    scale: Union[int, float] = 1
    dtype: str = "uint16"
    count: int = 1
    enum_map: Optional[Dict[int, str]] = None
    unique_id: Optional[str] = None


@dataclass
class SwitchRegister(RegisterDefinition):
    """Register definition for switch entities."""

    enum_map: Optional[Dict[int, str]] = None


@dataclass
class NumberRegister(RegisterDefinition):
    """Register definition for number entities."""

    scale: Union[int, float] = 1
    dtype: str = "uint16"
    min_value: Union[int, float] = 0
    max_value: Union[int, float] = 100
    step: Union[int, float] = 1
    enum_map: Optional[Dict[int, str]] = None


@dataclass
class SelectRegister(RegisterDefinition):
    """Register definition for select entities."""

    enum_map: Dict[int, str] = field(default_factory=dict)


@dataclass
class CalculatedRegister(RegisterDefinition):
    """Register definition for calculated sensors."""

    pass  # All fields are in base class
