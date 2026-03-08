import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

from . import NORMAL_SCAN_INTERVAL
from .const import DOMAIN, SLOW_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 502


def _entry_value(config_entry, key, default=None):
    """Read option value with fallback to legacy entry data."""
    options = getattr(config_entry, "options", {}) or {}
    data = getattr(config_entry, "data", {}) or {}
    return options.get(key, data.get(key, default))


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Minimaler Config Flow für Daikin Altherma 4 Modbus."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the user step."""
        errors = {}

        if user_input is not None:
            # Scan Interval Default setzen, falls nicht angegeben
            if "scan_interval" not in user_input:
                user_input["scan_interval"] = 10
            return self.async_create_entry(
                title=f"Daikin Altherma 4 ({user_input[CONF_HOST]})", data=user_input
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=""): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional("scan_interval", default=NORMAL_SCAN_INTERVAL): int,
                vol.Optional("slow_scan_interval", default=SLOW_SCAN_INTERVAL): int,
                vol.Optional("electric_power_sensor"): str,
                vol.Optional("demo_mode", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors, last_step=True
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Options flow for Daikin Altherma 4 Modbus."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        _LOGGER.debug(f"OptionsFlow step_init. User input: {user_input}")

        if user_input is not None:
            # Validate host
            host = user_input.get("host", "").strip()
            if not host:
                errors["host"] = "invalid_host"

            # Validate port
            port = user_input.get("port")
            if port is not None and (port < 1 or port > 65535):
                errors["port"] = "invalid_port"

            # If no errors, proceed with update
            if not errors:
                electric_power_sensor = user_input.get(
                    "electric_power_sensor", ""
                ).strip()
                options_data = {
                    "host": host,
                    "port": port if port is not None else DEFAULT_PORT,
                    "scan_interval": user_input.get(
                        "scan_interval", NORMAL_SCAN_INTERVAL
                    ),
                    "slow_scan_interval": user_input.get(
                        "slow_scan_interval", SLOW_SCAN_INTERVAL
                    ),
                    "demo_mode": user_input.get("demo_mode", False),
                }
                if electric_power_sensor:
                    options_data["electric_power_sensor"] = electric_power_sensor

                _LOGGER.debug("Updating config entry options: %s", options_data)
                return self.async_create_entry(title="", data=options_data)

        # Get current values
        current_host = _entry_value(self._config_entry, "host", "")
        current_port = _entry_value(self._config_entry, "port", DEFAULT_PORT)
        current_scan_interval = _entry_value(
            self._config_entry, "scan_interval", NORMAL_SCAN_INTERVAL
        )
        current_slow_scan_interval = _entry_value(
            self._config_entry, "slow_scan_interval", SLOW_SCAN_INTERVAL
        )
        current_electric_power_sensor = _entry_value(
            self._config_entry, "electric_power_sensor", ""
        )
        current_demo_mode = _entry_value(self._config_entry, "demo_mode", False)

        _LOGGER.debug(
            f"OptionsFlow showing form. Current values: host='{current_host}', port={current_port}, scan_interval={current_scan_interval}, slow_scan_interval={current_slow_scan_interval}, electric_power_sensor='{current_electric_power_sensor}'"
        )

        data_schema = vol.Schema(
            {
                vol.Required("host", default=current_host): str,
                vol.Optional("port", default=current_port): int,
                vol.Optional("scan_interval", default=current_scan_interval): int,
                vol.Optional(
                    "slow_scan_interval", default=current_slow_scan_interval
                ): int,
                vol.Optional(
                    "electric_power_sensor", default=current_electric_power_sensor
                ): str,
                vol.Optional("demo_mode", default=current_demo_mode): bool,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors, last_step=True
        )
