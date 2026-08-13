"""Repair flows for Daikin Altherma 4 Modbus integration."""

import logging

from homeassistant import config_entries

try:
    from homeassistant.const import CONF_HOST, CONF_PORT
except ImportError:
    CONF_HOST = "host"
    CONF_PORT = "port"

from .config_entry_utils import entry_data_value
from .config_flow import (
    _build_fix_schema,
    _is_valid_host,
    _test_connection,
)

_LOGGER = logging.getLogger(__name__)


class ConnectionLostFixFlow(config_entries.ConfigFlow):
    """Repair flow for reconfiguring connection after connection loss."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the fix flow."""
        self._entry_id: str | None = None

    async def async_step_init(self, user_input=None):
        """Handle the first step of the fix flow."""
        self._entry_id = self.context.get("entry_id")
        return await self.async_step_fix_connection()

    async def async_step_fix_connection(self, user_input=None):
        """Handle reconfiguration of connection settings."""
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        current_host = entry_data_value(entry, "host", "")
        current_port = entry_data_value(entry, "port", 502)

        if user_input is not None:
            host = user_input.get(CONF_HOST, "").strip()
            port = user_input.get(CONF_PORT, 502)

            # Validate
            if not _is_valid_host(host):
                return self.async_show_form(
                    step_id="fix_connection",
                    data_schema=_build_fix_schema(host, port),
                    errors={CONF_HOST: "invalid_host"},
                )

            if not (1 <= port <= 65535):
                return self.async_show_form(
                    step_id="fix_connection",
                    data_schema=_build_fix_schema(host, port),
                    errors={CONF_PORT: "invalid_port"},
                )

            # Test connection
            connection_ok, error_key = await _test_connection(host, port)
            if not connection_ok:
                return self.async_show_form(
                    step_id="fix_connection",
                    data_schema=_build_fix_schema(host, port),
                    errors={CONF_HOST: error_key},
                )

            # Update the config entry
            new_data = {
                CONF_HOST: host,
                CONF_PORT: port,
            }
            self.hass.config_entries.async_update_entry(
                entry,
                unique_id=f"{host}:{port}",
                data=new_data,
            )
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="fix_successful")

        return self.async_show_form(
            step_id="fix_connection",
            data_schema=_build_fix_schema(current_host, current_port),
            errors={},
        )
