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
        """Handle the user step."""
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
            vol.Optional("demo_mode", default=False): bool,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors,
            last_step=True
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
                # Process all options
                scan_interval = user_input.get("scan_interval")
                electric_power_sensor = user_input.get("electric_power_sensor")
                
                # Create options data
                options_data = {}
                
                # Update config entry data with connection parameters
                new_data = dict(self._config_entry.data)
                
                # Update host
                if host:
                    new_data["host"] = host
                    _LOGGER.debug(f"Updating host to: {host}")
                
                # Update port
                if port is not None:
                    new_data["port"] = port
                    _LOGGER.debug(f"Updating port to: {port}")
                
                # Update scan_interval
                if scan_interval is not None:
                    new_data["scan_interval"] = scan_interval
                    _LOGGER.debug(f"Updating scan_interval to: {scan_interval}")
                
                # Update electric_power_sensor
                if electric_power_sensor and electric_power_sensor.strip():
                    new_data["electric_power_sensor"] = electric_power_sensor.strip()
                    _LOGGER.debug(f"Updating electric_power_sensor to: {electric_power_sensor.strip()}")
                else:
                    if "electric_power_sensor" in new_data:
                        del new_data["electric_power_sensor"]
                        _LOGGER.debug("Removing electric_power_sensor")
                
                _LOGGER.debug(f"New config entry data will be: {new_data}")
                self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
                
                result = self.async_create_entry(title="", data=options_data)
                _LOGGER.debug(f"async_create_entry result: {result}")
                return result

        # Get current values
        current_host = self._config_entry.data.get("host", "")
        current_port = self._config_entry.data.get("port", DEFAULT_PORT)
        current_scan_interval = self._config_entry.data.get("scan_interval", 10)
        current_electric_power_sensor = self._config_entry.data.get("electric_power_sensor", "")
        
        _LOGGER.debug(f"OptionsFlow showing form. Current values: host='{current_host}', port={current_port}, scan_interval={current_scan_interval}, electric_power_sensor='{current_electric_power_sensor}'")
        
        data_schema = vol.Schema({
            vol.Required("host", default=current_host): str,
            vol.Optional("port", default=current_port): int,
            vol.Optional("scan_interval", default=current_scan_interval): int,
            vol.Optional("electric_power_sensor", default=current_electric_power_sensor): str,
        })

        return self.async_show_form(
            step_id="init", 
            data_schema=data_schema, 
            errors=errors,
            last_step=True
        )
