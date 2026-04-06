import ipaddress
import logging
import re

import voluptuous as vol
from homeassistant import config_entries

try:
    from homeassistant.const import CONF_HOST, CONF_PORT
except ImportError:
    # Fallback for testing when homeassistant is not available
    CONF_HOST = "host"
    CONF_PORT = "port"

from . import NORMAL_SCAN_INTERVAL
from .config_entry_utils import entry_value
from .const import DOMAIN, SLOW_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 502
HOSTNAME_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,63}$")


async def _test_connection(host: str, port: int) -> tuple[bool, str | None]:
    """Test Modbus connection to the device.

    Returns:
        Tuple of (success, error_message)
        - success: True if connection was successful
        - error_message: None if successful, otherwise the error description
    """
    try:
        # Import here to avoid issues during testing without dependencies
        from .modbus_client import RealModbusTcpClient

        _LOGGER.debug(f"Testing connection to {host}:{port}")
        client = await RealModbusTcpClient.create(host, port, timeout=10)

        # Try to connect
        await client.connect()

        if not client.connected:
            return False, "cannot_connect"

        # Try to read a basic register to verify device is responsive
        # Using input register 1 which should exist on most Modbus devices
        try:
            await client.read_input_registers(1, 1)
        except Exception as err:
            _LOGGER.debug(f"Connection test read failed: {err}")
            # Even if read fails, connection might be valid
            # Just verify we can connect

        # Disconnect after test
        await client.disconnect()

        _LOGGER.debug(f"Connection test successful to {host}:{port}")
        return True, None

    except Exception as err:
        _LOGGER.debug(f"Connection test failed to {host}:{port}: {err}")
        return False, "cannot_connect"


def _is_valid_host(host: str) -> bool:
    """Validate host as IP address or DNS hostname."""
    if not host or " " in host:
        return False

    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass

    if len(host) > 253:
        return False

    labels = host.split(".")
    for label in labels:
        if not label or not HOSTNAME_PATTERN.match(label):
            return False
        if label.startswith("-") or label.endswith("-"):
            return False

    return True


def _validate_common_values(
    host: str | None,
    port: int | None,
    scan_interval: int,
    slow_scan_interval: int,
) -> dict:
    """Validate config/options values and return HA form errors."""
    errors = {}

    if host is not None and not _is_valid_host(host):
        errors[CONF_HOST] = "invalid_host"

    if port is not None and not (1 <= port <= 65535):
        errors[CONF_PORT] = "invalid_port"

    if scan_interval <= 0:
        errors["scan_interval"] = "invalid_scan_interval"

    if slow_scan_interval < scan_interval:
        errors["slow_scan_interval"] = "slow_must_be_gte_scan"

    return errors


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Minimaler Config Flow für Daikin Altherma 4 Modbus."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the user step."""
        errors = {}
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

        if user_input is not None:
            host = user_input.get(CONF_HOST, "").strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            scan_interval = user_input.get("scan_interval", NORMAL_SCAN_INTERVAL)
            slow_scan_interval = user_input.get(
                "slow_scan_interval", SLOW_SCAN_INTERVAL
            )
            errors = _validate_common_values(
                host=host,
                port=port,
                scan_interval=scan_interval,
                slow_scan_interval=slow_scan_interval,
            )
            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=data_schema,
                    errors=errors,
                    last_step=True,
                )

            # Test connection to device (unless in demo mode)
            demo_mode = user_input.get("demo_mode", False)
            if not demo_mode:
                connection_ok, error_key = await _test_connection(host, port)
                if not connection_ok:
                    errors = {CONF_HOST: error_key}
                    return self.async_show_form(
                        step_id="user",
                        data_schema=data_schema,
                        errors=errors,
                        last_step=True,
                    )

            data = {
                CONF_HOST: host,
                CONF_PORT: port,
            }
            options = {
                "scan_interval": scan_interval,
                "slow_scan_interval": slow_scan_interval,
                "demo_mode": demo_mode,
            }
            electric_power_sensor = user_input.get("electric_power_sensor", "").strip()
            if electric_power_sensor:
                options["electric_power_sensor"] = electric_power_sensor
            return self.async_create_entry(
                title=f"Daikin Altherma 4 ({host})",
                data=data,
                options=options,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            last_step=True,
            data_description={
                CONF_HOST: "IP address of your Daikin Altherma 4 heat pump (e.g., 192.168.1.100)",
                CONF_PORT: "Modbus TCP port (default: 502, use 802 for TLS)",
                "scan_interval": "Polling interval in seconds for normal sensors (default: 5)",
                "slow_scan_interval": "Polling interval in seconds for slow-changing sensors (default: 30)",
                "electric_power_sensor": "Optional: Entity ID of external power sensor for CoP calculation (e.g., sensor.shelly_em_power)",
                "demo_mode": "Enable demo mode for testing without actual hardware",
            },
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
            scan_interval = user_input.get("scan_interval", NORMAL_SCAN_INTERVAL)
            slow_scan_interval = user_input.get(
                "slow_scan_interval", SLOW_SCAN_INTERVAL
            )
            errors = _validate_common_values(
                host=None,
                port=None,
                scan_interval=scan_interval,
                slow_scan_interval=slow_scan_interval,
            )

            # If no errors, proceed with update
            if not errors:
                electric_power_sensor = user_input.get(
                    "electric_power_sensor", ""
                ).strip()
                options_data = {
                    "scan_interval": scan_interval,
                    "slow_scan_interval": slow_scan_interval,
                    "demo_mode": user_input.get("demo_mode", False),
                }
                if electric_power_sensor:
                    options_data["electric_power_sensor"] = electric_power_sensor

                _LOGGER.debug("Updating config entry options: %s", options_data)
                return self.async_create_entry(title="", data=options_data)

        # Get current values
        current_scan_interval = entry_value(
            self._config_entry, "scan_interval", NORMAL_SCAN_INTERVAL
        )
        current_slow_scan_interval = entry_value(
            self._config_entry, "slow_scan_interval", SLOW_SCAN_INTERVAL
        )
        current_electric_power_sensor = entry_value(
            self._config_entry, "electric_power_sensor", ""
        )
        current_demo_mode = entry_value(self._config_entry, "demo_mode", False)

        _LOGGER.debug(
            "OptionsFlow showing form. Current values: scan_interval=%s, "
            "slow_scan_interval=%s, electric_power_sensor='%s', demo_mode=%s",
            current_scan_interval,
            current_slow_scan_interval,
            current_electric_power_sensor,
            current_demo_mode,
        )

        data_schema = vol.Schema(
            {
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
            step_id="init",
            data_schema=data_schema,
            errors=errors,
            last_step=True,
            data_description={
                "scan_interval": "Polling interval in seconds for normal sensors (default: 5)",
                "slow_scan_interval": "Polling interval in seconds for slow-changing sensors (default: 30)",
                "electric_power_sensor": "Optional: Entity ID of external power sensor for CoP calculation (e.g., sensor.shelly_em_power)",
                "demo_mode": "Enable demo mode for testing without actual hardware",
            },
        )
