import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

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
                title=f"Daikin Altherma 4 ({user_input[CONF_HOST]})",
                data=user_input
            )

        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default=""): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Optional("scan_interval", default=10): int,
            vol.Optional("electric_power_sensor"): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Options flow für Daikin Altherma 4 Modbus."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        _LOGGER.info(f"OptionsFlow step_init. User input: {user_input}")

        if user_input is not None:
            # Process the electric_power_sensor value
            electric_power_sensor = user_input.get("electric_power_sensor")
            
            # Create options data
            options_data = {}
            if electric_power_sensor and electric_power_sensor.strip():
                options_data["electric_power_sensor"] = electric_power_sensor.strip()
                _LOGGER.info(f"Setting electric_power_sensor to: {electric_power_sensor.strip()}")
            else:
                # Don't include the key in options_data for deletion
                _LOGGER.info("Removing electric_power_sensor (empty/None value)")
            
            _LOGGER.info(f"Creating entry with options data: {options_data}")
            
            # Update the config entry data directly
            new_data = dict(self._config_entry.data)
            if electric_power_sensor and electric_power_sensor.strip():
                new_data["electric_power_sensor"] = electric_power_sensor.strip()
                _LOGGER.info(f"Updating config entry: setting electric_power_sensor to {electric_power_sensor.strip()}")
            else:
                if "electric_power_sensor" in new_data:
                    del new_data["electric_power_sensor"]
                    _LOGGER.info("Updating config entry: removing electric_power_sensor")
            
            _LOGGER.info(f"New config entry data will be: {new_data}")
            self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
            
            result = self.async_create_entry(title="", data=options_data)
            _LOGGER.info(f"async_create_entry result: {result}")
            return result

        current_value = self._config_entry.data.get("electric_power_sensor", "")
        _LOGGER.info(f"OptionsFlow showing form. Current electric_power_sensor: '{current_value}'")
        
        data_schema = vol.Schema({
            vol.Optional(
                "electric_power_sensor",
                default=current_value
            ): str,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
