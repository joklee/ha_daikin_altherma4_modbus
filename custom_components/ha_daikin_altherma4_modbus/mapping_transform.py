"""Mapping/transform layer for raw Modbus responses."""

import logging
from typing import Any, Dict, List

from .common import to_signed_16bit, update_value_if_changed
from .const import CALCULATED_SENSORS
from .data_types import (
    LastTriggeredData,
    ProcessedRegisterItem,
    StateData,
    StateMapping,
)

_LOGGER = logging.getLogger(__name__)


class ModbusMappingTransform:
    """Transforms raw responses to integration entity state dictionaries."""

    def __init__(self):
        self.previous_data: StateData = {}
        self.last_triggered: LastTriggeredData = {}

    @staticmethod
    def process_register_block(
        register_data,
        register_list: List[Dict[str, Any]],
        min_address: int,
        max_address: int,
        offset: int,
        default_input_type: str,
        register_description: str,
    ) -> Dict[str, ProcessedRegisterItem]:
        """Build raw register map for a configured address range."""
        data: Dict[str, ProcessedRegisterItem] = {}
        for item in register_list:
            address = item["address"]
            input_type = item.get("input_type", default_input_type)
            register_name = item.get("register_name")
            if min_address <= address <= max_address:
                try:
                    raw_value = register_data.registers[address]
                except IndexError as err:
                    _LOGGER.error(
                        "IndexError accessing register %s: %s, array_len=%s",
                        address,
                        err,
                        len(register_data.registers),
                    )
                    raise

                data[register_name] = {
                    "raw_value": raw_value,
                    "input_type": input_type,
                    "address": address,
                    "description": f"{register_description} {address}",
                    "item": item,
                }

        return data

    @staticmethod
    def apply_register_processing(
        register_name: str,
        processed_item: ProcessedRegisterItem,
        previous_data: StateMapping,
        include_scale: bool = True,
    ):
        """Apply scaling and unavailable handling to processed register payload."""
        raw_value = processed_item["raw_value"]
        input_type = processed_item["input_type"]
        address = processed_item["address"]
        description = processed_item["description"]
        item = processed_item["item"]

        if "scale" in item:
            # Convert signed 16-bit integers before scaling (for int16 dtype)
            if item.get("dtype") == "int16":
                raw_value = to_signed_16bit(raw_value)

            if raw_value == 32765 or raw_value == 32766:
                return update_value_if_changed(
                    register_name,
                    raw_value,
                    previous_data,
                    description,
                    input_type=input_type,
                    address=address,
                    scale=item["scale"],
                )

            scaled_value = round(raw_value * item["scale"], 2)
            return update_value_if_changed(
                register_name,
                scaled_value,
                previous_data,
                description,
                input_type=input_type,
                address=address,
                scale=item["scale"],
            )

        kwargs = {
            "register_name": register_name,
            "value": raw_value,
            "previous_data": previous_data,
            "description": description,
            "input_type": input_type,
            "address": address,
        }
        if include_scale:
            kwargs["scale"] = 1
        return update_value_if_changed(**kwargs)

    def process_input_register_block(
        self,
        register_data,
        register_list: List[Dict[str, Any]],
        min_address: int,
        max_address: int,
        offset: int,
    ) -> StateData:
        """Process a block of input registers."""
        processed_data = self.process_register_block(
            register_data,
            register_list,
            min_address,
            max_address,
            offset,
            "input",
            "Input Register",
        )

        data: StateData = {}
        for register_name, processed_item in processed_data.items():
            raw_value = processed_item["raw_value"]
            item = processed_item["item"]
            input_type = processed_item["input_type"]
            address = processed_item["address"]
            description = processed_item["description"]

            if item.get("enum_map"):
                if raw_value == 32766 and len(item["enum_map"]) <= 2:
                    continue
                data[register_name] = update_value_if_changed(
                    register_name,
                    raw_value,
                    self.previous_data,
                    description,
                    input_type=input_type,
                    address=address,
                )
            else:
                data[register_name] = self.apply_register_processing(
                    register_name,
                    processed_item,
                    self.previous_data,
                    include_scale=False,
                )

        return data

    def process_holding_register_block(
        self,
        register_data,
        register_list: List[Dict[str, Any]],
        min_address: int,
        max_address: int,
        offset: int,
    ) -> StateData:
        """Process a block of holding registers."""
        processed_data = self.process_register_block(
            register_data,
            register_list,
            min_address,
            max_address,
            offset,
            "holding",
            "Holding Register",
        )

        data: StateData = {}
        for register_name, processed_item in processed_data.items():
            data[register_name] = self.apply_register_processing(
                register_name, processed_item, self.previous_data
            )
        return data

    def process_bit_sensors(
        self, result, sensor_list: List[Dict[str, Any]], sensor_type: str
    ) -> StateData:
        """Process bit-based sensors from Modbus bit response."""
        data: StateData = {}
        for item in sensor_list:
            address = item["address"]
            input_type = item.get("input_type", sensor_type)
            register_name = item.get("register_name")

            if address < len(result.bits):
                raw_value = 1 if result.bits[address] else 0
                data[register_name] = update_value_if_changed(
                    register_name,
                    raw_value,
                    self.previous_data,
                    f"{sensor_type.title()} {address}",
                    input_type=input_type,
                    address=address,
                )
            else:
                _LOGGER.warning(
                    "%s %s nicht im gelesenen Bereich (%s Bits)",
                    sensor_type.title(),
                    address,
                    len(result.bits),
                )

        return data

    def update_last_triggered(self, data: StateData) -> None:
        """Update timestamp-style calculated trigger sensors."""
        from homeassistant.util import dt as dt_util

        for item in CALCULATED_SENSORS:
            if item.get("trigger_register_name") is None:
                continue

            register_name = item.get("register_name")
            trigger_register_name = item.get("trigger_register_name")

            current_data = data.get(trigger_register_name, {})
            current_val = current_data.get("value")
            previous_data = self.previous_data.get(trigger_register_name, {})
            previous_val = previous_data.get("value")

            is_on = current_val == 1
            was_on = previous_val == 1 if previous_val is not None else False
            if is_on and not was_on:
                self.last_triggered[register_name] = dt_util.now()

            if register_name in self.last_triggered:
                data[register_name] = {
                    "value": self.last_triggered[register_name],
                    "input_type": "calculated",
                    "register_name": register_name,
                }
