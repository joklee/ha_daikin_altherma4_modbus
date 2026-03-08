"""Typed data models for Modbus register/state payloads."""

from datetime import datetime
from typing import Any, Dict, Mapping, MutableMapping, TypedDict, Union


RegisterValue = Union[int, float, str, datetime, None]


class EntityStatePayload(TypedDict, total=False):
    """Normalized state payload stored per register/entity."""

    value: RegisterValue
    input_type: str
    address: int
    register_name: str
    description: str
    scale: Union[int, float]
    last_updated: float


class ProcessedRegisterItem(TypedDict):
    """Intermediate payload used while transforming raw register blocks."""

    raw_value: int
    input_type: str
    address: int
    description: str
    item: Dict[str, Any]


StateData = Dict[str, EntityStatePayload]
StateMapping = Mapping[str, EntityStatePayload]
MutableStateMapping = MutableMapping[str, EntityStatePayload]
LastTriggeredData = Dict[str, datetime]
