"""Typed data models for Modbus register/state payloads."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, MutableMapping, Union

RegisterValue = Union[int, float, str, datetime, None]


@dataclass
class EntityStatePayload:
    """Normalized state payload stored per register/entity."""

    value: RegisterValue = None
    input_type: str = ""
    address: int = 0
    register_name: str = ""
    description: str = ""
    scale: Union[int, float] = 1
    last_updated: float = 0.0


@dataclass
class ProcessedRegisterItem:
    """Intermediate payload used while transforming raw register blocks."""

    raw_value: int
    input_type: str
    address: int
    description: str
    item: Dict[str, Any] = field(default_factory=dict)


StateData = Dict[str, EntityStatePayload]
StateMapping = Mapping[str, EntityStatePayload]
MutableStateMapping = MutableMapping[str, EntityStatePayload]
LastTriggeredData = Dict[str, datetime]
