"""Entities module for Daikin Altherma 4 Modbus integration."""

from .binary_sensor import DaikinBinarySensor, DaikinDiscreteInputSensor
from .climate import DaikinDHWThermostat, DaikinThermostatClimate
from .number import DaikinNumber
from .select import DaikinSelect
from .sensor import (
    CalculatedCoPSensor,
    DaikinInputSensor,
    DeltaTSensor,
    ExternalElectricPowerSensor,
    LastTriggeredSensor,
    ThermalHeatOutput,
)
from .switch import DaikinCoilSwitch, DaikinHoldingSwitch

__all__ = [
    "CalculatedCoPSensor",
    "DaikinBinarySensor",
    "DaikinCoilSwitch",
    "DaikinDHWThermostat",
    "DaikinDiscreteInputSensor",
    "DaikinHoldingSwitch",
    "DaikinInputSensor",
    "DaikinNumber",
    "DaikinSelect",
    "DaikinThermostatClimate",
    "DeltaTSensor",
    "ExternalElectricPowerSensor",
    "LastTriggeredSensor",
    "ThermalHeatOutput",
]
