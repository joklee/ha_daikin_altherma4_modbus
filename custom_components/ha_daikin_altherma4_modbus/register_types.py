"""Register definition dataclasses for type-safe Modbus register handling."""

from dataclasses import dataclass, field

from homeassistant.const import EntityCategory

__all__ = [
    "BIT",
    "INT16",
    "INT16S100",
    "POW16",
    "TEMP16",
    "TEXT16",
    "TIMESTAMP16",
    "CalculatedRegister",
    "NumberRegister",
    "RegisterDataType",
    "RegisterDefinition",
    "SelectRegister",
    "SensorRegister",
    "SwitchRegister",
]


@dataclass
class RegisterDataType:
    """Data type definition for Modbus registers with scaling and range information."""

    name: str
    signed: bool
    bits: int
    scaling: int | float
    range: tuple[int | float, int | float] | None = None


# Predefined register data types
TEMP16 = RegisterDataType(
    name="Temp16", signed=True, bits=16, scaling=0.01, range=(-327.68, 327.67)
)

INT16 = RegisterDataType(
    name="Int16", signed=True, bits=16, scaling=1, range=(-32768, 32767)
)

INT16S100 = RegisterDataType(
    name="Int16", signed=True, bits=16, scaling=0.01, range=(-32768, 32767)
)

TEXT16 = RegisterDataType(name="Text16", signed=False, bits=16, scaling=1, range=None)

POW16 = RegisterDataType(
    name="Pow16", signed=True, bits=16, scaling=0.01, range=(-327.68, 327.67)
)

BIT = RegisterDataType(name="Bit", signed=False, bits=1, scaling=1, range=(0, 1))

TIMESTAMP16 = RegisterDataType(
    name="Timestamp16", signed=False, bits=16, scaling=1, range=(0, 65535)
)


@dataclass
class RegisterDefinition:
    """Base class for all register definitions."""

    name: str
    address: int
    input_type: str
    register_name: str
    data_type: RegisterDataType
    calc_type: str | None = None  # For calculated registers
    trigger_register_name: str | None = None  # For calculated registers

    # Optional fields with defaults
    unit: str | None = None
    device_class: str | None = None
    icon: str | None = None
    translation_key: str | None = None
    entity_category: EntityCategory | None = None
    step: int | float | None = None


@dataclass
class SensorRegister(RegisterDefinition):
    """Register definition for sensor entities."""

    count: int = 1
    enum_map: dict[int, str] | None = None
    unique_id: str | None = None


@dataclass
class SwitchRegister(RegisterDefinition):
    """Register definition for switch entities."""

    enum_map: dict[int, str] | None = None


@dataclass
class NumberRegister(RegisterDefinition):
    """Register definition for number entities."""

    min_value: int | float = 0
    max_value: int | float = 100
    step: int | float = 1
    enum_map: dict[int, str] | None = None


@dataclass
class SelectRegister(RegisterDefinition):
    """Register definition for select entities."""

    enum_map: dict[int, str] = field(default_factory=dict)
    min_value: int | float = 0
    max_value: int | float = 100
    step: int | float = 1


@dataclass
class CalculatedRegister(RegisterDefinition):
    """Register definition for calculated sensors."""

    # All fields are in base class
