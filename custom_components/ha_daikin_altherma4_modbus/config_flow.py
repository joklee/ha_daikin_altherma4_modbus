import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN

DEFAULT_PORT = 502

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Minimaler Config Flow für Daikin Altherma 4 Modbus."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Schritt für Benutzer-Eingabe (Host, Port, Scan Interval)."""
        errors = {}

        if user_input is not None:
            # Scan Interval Default setzen, falls nicht angegeben
            if "scan_interval" not in user_input:
                user_input["scan_interval"] = 10
            return self.async_create_entry(
                title=f"Daikin Altherma 4{user_input[CONF_HOST]}",
                data=user_input
            )

        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default=""): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Optional("scan_interval", default=10): int,
            vol.Optional("electric_power_sensor"): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
