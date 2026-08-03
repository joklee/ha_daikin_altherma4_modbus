"""Typed data models for Modbus register/state payloads."""

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

RegisterValue = int | float | str | datetime | None


@dataclass
class EntityStatePayload:
    """Normalized state payload stored per register/entity."""

    value: RegisterValue = None
    input_type: str = ""
    address: int = 0
    register_name: str = ""
    description: str = ""
    scale: int | float = 1
    last_updated: float = 0.0


@dataclass
class ProcessedRegisterItem:
    """Intermediate payload used while transforming raw register blocks."""

    raw_value: int
    input_type: str
    address: int
    description: str
    item: dict[str, Any] = field(default_factory=dict)


StateData = dict[str, EntityStatePayload]
StateMapping = Mapping[str, EntityStatePayload]
MutableStateMapping = MutableMapping[str, EntityStatePayload]
LastTriggeredData = dict[str, datetime]
