"""Diagnostics for Daikin Altherma 4 Modbus.

Home Assistant resolves the diagnostics platform by importing
``custom_components.<domain>.diagnostics``; the implementation lives in
``integration/diagnostics.py`` and is re-exported here.
"""

from .integration.diagnostics import async_get_config_entry_diagnostics

__all__ = ["async_get_config_entry_diagnostics"]
