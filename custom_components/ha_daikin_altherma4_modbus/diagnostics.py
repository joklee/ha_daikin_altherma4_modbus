"""Diagnostics support for Daikin Altherma 4 Modbus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

TO_REDACT = {"host"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = entry.runtime_data
    manager = runtime_data.manager

    # Collect coordinator data
    coordinator_data = {}
    for coord_name, coordinator in manager.coordinators.items():
        if coordinator.data:
            # Convert data to serializable format
            serializable = {}
            for key, value in coordinator.data.items():
                if hasattr(value, "__dict__"):
                    serializable[key] = {
                        "value": getattr(value, "value", None),
                        "input_type": getattr(value, "input_type", None),
                        "register_name": getattr(value, "register_name", str(key)),
                    }
                elif isinstance(value, dict):
                    serializable[key] = value
                else:
                    serializable[key] = {"value": value}
            coordinator_data[coord_name] = serializable

    # Coordinator statuses
    coordinator_statuses = {}
    for coord_name, coordinator in manager.coordinators.items():
        coordinator_statuses[coord_name] = {
            "last_update_success": coordinator.last_update_success,
            "update_interval": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "data_points": len(coordinator.data) if coordinator.data else 0,
        }

    diagnostics_data = {
        "config_entry_data": dict(entry.data),
        "config_entry_options": dict(entry.options),
        "connection": {
            "host": manager.host,
            "port": manager.port,
            "demo_mode": manager.demo_mode,
        },
        "coordinator_statuses": coordinator_statuses,
        "coordinator_data": coordinator_data,
    }

    return {
        "config_entry_data": async_redact_data(
            diagnostics_data["config_entry_data"], TO_REDACT
        ),
        "config_entry_options": diagnostics_data["config_entry_options"],
        "connection": async_redact_data(diagnostics_data["connection"], TO_REDACT),
        "coordinator_statuses": diagnostics_data["coordinator_statuses"],
        "coordinator_data": diagnostics_data["coordinator_data"],
    }
