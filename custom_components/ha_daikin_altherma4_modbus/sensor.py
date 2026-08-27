"""Sensor platform for the Daikin Altherma 4 Modbus integration.

Home Assistant resolves entity platforms by importing
``custom_components.<domain>.<platform>``; the implementation lives in
``entities/sensor.py`` and is re-exported here.
"""

from .entities.sensor import async_setup_entry

__all__ = ["async_setup_entry"]
