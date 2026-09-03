"""Config flow tests for ha_daikin_altherma4_modbus integration."""

import pytest

pytestmark = [pytest.mark.config_flow]

from unittest import mock

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.integration import (
    config_flow as config_flow_module,
)
from custom_components.ha_daikin_altherma4_modbus.integration.config_flow import (
    ConfigFlow,
    OptionsFlow,
)
from custom_components.ha_daikin_altherma4_modbus.modbus.modbus_client import (
    RealModbusTcpClient,
)


class _FakeModbusClient:
    """Minimal Modbus client double for config-flow connection tests."""

    def __init__(self, connected: bool = True) -> None:
        self._connected = connected

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Keep connection state controlled by the constructor."""

    async def disconnect(self) -> None:
        self._connected = False

    async def read_input_registers(self, address: int, count: int):
        return type("Response", (), {"registers": [0] * count})()


@pytest.mark.asyncio
async def test_config_flow_success(hass, enable_custom_integrations):
    """Test successful config flow execution."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "electric_power_sensor": "sensor.power",
            "demo_mode": True,
        },
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Daikin Altherma 4 (192.168.1.100)"
    assert result["data"] == {CONF_HOST: "192.168.1.100", CONF_PORT: 502}
    assert result["options"] == {
        "scan_interval": 15,
        "slow_scan_interval": 300,
        "electric_power_sensor": "sensor.power",
        "demo_mode": True,
    }


@pytest.mark.asyncio
async def test_config_flow_invalid_host(hass, enable_custom_integrations):
    """Test config flow with invalid host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "invalid host with spaces",
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert "errors" in result
    assert result["errors"][CONF_HOST] == "invalid_host"


@pytest.mark.asyncio
async def test_config_flow_connection_error(hass, enable_custom_integrations):
    """Test config flow with connection error - connection test fails."""
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClient(connected=False)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": False,  # Not demo mode, so connection test runs
            },
        )

    assert result["type"] == "form"
    assert "errors" in result
    assert result["errors"][CONF_HOST] == "cannot_connect"


@pytest.mark.asyncio
async def test_config_flow_connection_success_demo_mode(
    hass, enable_custom_integrations
):
    """Test config flow skips connection test in demo mode."""
    # Even when the Modbus connection would fail, demo mode should bypass the
    # connection test entirely.
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(side_effect=ConnectionError("device not reachable")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": True,  # Demo mode skips connection test
            },
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Daikin Altherma 4 (192.168.1.100)"


@pytest.mark.asyncio
async def test_options_flow(hass, enable_custom_integrations):
    """Test options flow execution."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
            "electric_power_sensor": "existing_sensor",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Mock user input with updated values
    user_input = {
        "scan_interval": 20,
        "slow_scan_interval": 400,
        "demo_mode": True,
        "electric_power_sensor": "new_sensor",
    }

    # Execute the options step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )

    # Verify successful creation of entry
    assert result["type"] == "create_entry"
    assert result["title"] == ""

    # Verify the updated options
    options_data = result["data"]
    assert options_data["scan_interval"] == 20
    assert options_data["slow_scan_interval"] == 400
    assert options_data["demo_mode"] is True
    assert options_data["electric_power_sensor"] == "new_sensor"


@pytest.mark.asyncio
async def test_options_flow_validation_errors(hass, enable_custom_integrations):
    """Test options flow validation errors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    # Test invalid scan_interval (<= 0)
    user_input = {
        "scan_interval": 0,
        "slow_scan_interval": 300,
        "demo_mode": False,
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )

    # Should return form with errors
    assert result["type"] == "form"
    assert "errors" in result
    assert "scan_interval" in result["errors"]
    assert result["errors"]["scan_interval"] == "invalid_scan_interval"

    # Test slow_scan_interval < scan_interval
    user_input = {
        "scan_interval": 20,
        "slow_scan_interval": 10,  # Less than scan_interval
        "demo_mode": False,
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )

    # Should return form with errors
    assert result["type"] == "form"
    assert "errors" in result
    assert "slow_scan_interval" in result["errors"]
    assert result["errors"]["slow_scan_interval"] == "slow_must_be_gte_scan"


@pytest.mark.asyncio
async def test_config_flow_show_form_no_input(hass, enable_custom_integrations):
    """Test config flow shows form when no user input provided."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=None,
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    assert result["last_step"] is True


@pytest.mark.asyncio
async def test_config_flow_empty_electric_power_sensor(
    hass, enable_custom_integrations
):
    """Test config flow excludes empty electric_power_sensor from options."""
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClient(connected=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "electric_power_sensor": "",  # Empty string
                "demo_mode": False,
            },
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Daikin Altherma 4 (192.168.1.100)"
    assert result["data"] == {CONF_HOST: "192.168.1.100", CONF_PORT: 502}
    # Empty electric_power_sensor should not be in options
    assert "electric_power_sensor" not in result["options"]
    assert result["options"]["scan_interval"] == 15
    assert result["options"]["demo_mode"] is False


@pytest.mark.asyncio
async def test_config_flow_invalid_port_low(hass, enable_custom_integrations):
    """Test config flow with port < 1."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 0,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_PORT] == "invalid_port"


@pytest.mark.asyncio
async def test_config_flow_invalid_port_high(hass, enable_custom_integrations):
    """Test config flow with port > 65535."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 65536,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_PORT] == "invalid_port"


@pytest.mark.asyncio
async def test_config_flow_invalid_scan_interval_zero(hass, enable_custom_integrations):
    """Test config flow with scan_interval = 0."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            "scan_interval": 0,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"]["scan_interval"] == "invalid_scan_interval"


@pytest.mark.asyncio
async def test_config_flow_invalid_scan_interval_negative(
    hass, enable_custom_integrations
):
    """Test config flow with negative scan_interval."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            "scan_interval": -5,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"]["scan_interval"] == "invalid_scan_interval"


@pytest.mark.asyncio
async def test_config_flow_slow_less_than_scan(hass, enable_custom_integrations):
    """Test config flow with slow_scan_interval < scan_interval."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            "scan_interval": 30,
            "slow_scan_interval": 20,  # Less than scan_interval
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"]["slow_scan_interval"] == "slow_must_be_gte_scan"


@pytest.mark.asyncio
async def test_options_flow_show_form_with_current_values(
    hass, enable_custom_integrations
):
    """Test that options flow shows form with current values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={
            "scan_interval": 25,
            "slow_scan_interval": 500,
            "demo_mode": True,
            "electric_power_sensor": "test_sensor",
        },
    )
    entry.add_to_hass(hass)

    # Call without user input to show form
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Verify form is shown
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Verify schema contains current values as defaults
    schema = result["data_schema"].schema
    assert "scan_interval" in schema
    assert "slow_scan_interval" in schema
    assert "demo_mode" in schema
    assert "electric_power_sensor" in schema


@pytest.mark.asyncio
async def test_options_flow_empty_electric_power_sensor(
    hass, enable_custom_integrations
):
    """Test that options flow excludes empty electric_power_sensor from options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
            "electric_power_sensor": "existing_sensor",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    # Provide empty electric_power_sensor
    user_input = {
        "scan_interval": 20,
        "slow_scan_interval": 400,
        "demo_mode": True,
        "electric_power_sensor": "",  # Empty string
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )

    # Verify successful creation of entry
    assert result["type"] == "create_entry"
    # Empty electric_power_sensor should not be in options
    assert "electric_power_sensor" not in result["data"]
    assert result["data"]["scan_interval"] == 20
    assert result["data"]["demo_mode"] is True


@pytest.mark.asyncio
async def test_config_flow_ipv6_host(hass, enable_custom_integrations):
    """Test config flow with IPv6 address."""
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClient(connected=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "::1",  # IPv6 localhost
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": False,
            },
        )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "::1"


@pytest.mark.asyncio
async def test_config_flow_valid_hostname(hass, enable_custom_integrations):
    """Test config flow with valid hostname."""
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClient(connected=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "heatpump.local",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": False,
            },
        )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "heatpump.local"


@pytest.mark.asyncio
async def test_config_flow_empty_host(hass, enable_custom_integrations):
    """Test config flow with empty host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "",
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_HOST] == "invalid_host"


@pytest.mark.asyncio
async def test_config_flow_hostname_too_long(hass, enable_custom_integrations):
    """Test config flow with hostname exceeding 253 chars."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "a" * 254,  # Too long
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_HOST] == "invalid_host"


@pytest.mark.asyncio
async def test_config_flow_hostname_hyphen_edge_cases(hass, enable_custom_integrations):
    """Test config flow with hostname starting/ending with hyphen."""
    # Hostname starting with hyphen
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "-invalid.local",
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_HOST] == "invalid_host"

    # Hostname ending with hyphen
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "invalid-.local",
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_HOST] == "invalid_host"


@pytest.mark.asyncio
async def test_config_flow_hostname_empty_label(hass, enable_custom_integrations):
    """Test config flow with empty label in hostname."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "invalid..host.local",  # Empty label between dots
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_HOST] == "invalid_host"


@pytest.mark.asyncio
async def test_async_get_options_flow(hass, enable_custom_integrations):
    """Test that async_get_options_flow returns OptionsFlow instance."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15},
    )

    flow = ConfigFlow()
    options_flow = flow.async_get_options_flow(config_entry)

    assert isinstance(options_flow, OptionsFlow)
    assert options_flow._config_entry == config_entry


@pytest.mark.asyncio
async def test_config_flow_connection_read_register_exception(
    hass, enable_custom_integrations
):
    """Test config flow when read_input_registers raises but connection succeeds."""

    class _FakeModbusClientReadError(_FakeModbusClient):
        async def read_input_registers(self, address: int, count: int):
            raise ConnectionError("Read failed but connection is valid")

    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClientReadError(connected=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": False,
            },
        )

    # Should still create entry even if read_input_registers raises
    assert result["type"] == "create_entry"
    assert result["title"] == "Daikin Altherma 4 (192.168.1.100)"


@pytest.mark.asyncio
async def test_config_flow_connection_client_create_exception(
    hass, enable_custom_integrations
):
    """Test config flow when RealModbusTcpClient.create raises exception."""
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(side_effect=ConnectionError("Failed to create client")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": False,
            },
        )

    # Should return form with connection error
    assert result["type"] == "form"
    assert "errors" in result
    assert result["errors"][CONF_HOST] == "cannot_connect"


@pytest.mark.asyncio
async def test_config_flow_single_label_hostname(hass, enable_custom_integrations):
    """Test config flow with single label hostname."""
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClient(connected=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "localhost",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": False,
            },
        )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "localhost"


@pytest.mark.asyncio
async def test_config_flow_hostname_with_only_numbers(hass, enable_custom_integrations):
    """Test config flow with hostname containing only numbers."""
    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClient(connected=True)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "123456",
                CONF_PORT: 502,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": False,
            },
        )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "123456"


@pytest.mark.asyncio
async def test_options_flow_missing_keys_in_input(hass, enable_custom_integrations):
    """Test options flow when some keys are missing from user input."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": False,
            "electric_power_sensor": "existing_sensor",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    # Provide partial input (missing electric_power_sensor)
    user_input = {
        "scan_interval": 20,
        "slow_scan_interval": 400,
        "demo_mode": True,
        # electric_power_sensor is missing
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )

    # Should still create entry with provided values
    assert result["type"] == "create_entry"
    assert result["data"]["scan_interval"] == 20
    assert result["data"]["slow_scan_interval"] == 400
    assert result["data"]["demo_mode"] is True
    # The real HA flow applies the options schema, which fills missing keys
    # with the current option values used as form defaults.
    assert result["data"]["electric_power_sensor"] == "existing_sensor"


@pytest.mark.asyncio
async def test_config_flow_uses_homeassistant_const(hass, enable_custom_integrations):
    """Test config flow resolves CONF_HOST/CONF_PORT from Home Assistant.

    The integration imports the connection constants from
    ``homeassistant.const`` at module import time. In a real HA environment
    this import always succeeds, so the module-level constants must be the
    ones provided by Home Assistant.
    """
    assert config_flow_module.CONF_HOST is CONF_HOST
    assert config_flow_module.CONF_PORT is CONF_PORT


@pytest.mark.asyncio
async def test_config_flow_reauth_shows_form(hass, enable_custom_integrations):
    """Test reauth flow shows form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "reauth"


@pytest.mark.asyncio
async def test_config_flow_reauth_success(hass, enable_custom_integrations):
    """Test reauth flow success."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15},
    )
    entry.add_to_hass(hass)

    # Reload would load the whole integration; it is only asserted here.
    with mock.patch.object(hass.config_entries, "async_reload", new=mock.AsyncMock()):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
            data={
                CONF_HOST: "192.168.1.200",
                CONF_PORT: 502,
                "scan_interval": 20,
                "slow_scan_interval": 400,
                "demo_mode": True,
            },
        )

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_HOST] == "192.168.1.200"
    assert entry.options["scan_interval"] == 20


@pytest.mark.asyncio
async def test_config_flow_reauth_invalid_host(hass, enable_custom_integrations):
    """Test reauth flow with invalid host."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data={
            CONF_HOST: "invalid host with spaces",
            CONF_PORT: 502,
            "scan_interval": 20,
            "slow_scan_interval": 400,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "reauth"
    assert "errors" in result
    assert result["errors"][CONF_HOST] == "invalid_host"


@pytest.mark.asyncio
async def test_config_flow_reconfigure_shows_form(hass, enable_custom_integrations):
    """Test reconfigure flow shows form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"


@pytest.mark.asyncio
async def test_config_flow_reconfigure_success(hass, enable_custom_integrations):
    """Test reconfigure flow updates data, options and unique_id, then reloads."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15, "electric_power_sensor": "sensor.power"},
    )
    entry.add_to_hass(hass)

    # Reload would load the whole integration; it is only asserted here.
    with mock.patch.object(
        hass.config_entries, "async_reload", new=mock.AsyncMock()
    ) as reload_mock:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={
                CONF_HOST: "192.168.1.200",
                CONF_PORT: 502,
                "scan_interval": 20,
                "slow_scan_interval": 400,
                "demo_mode": True,
            },
        )

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_HOST: "192.168.1.200", CONF_PORT: 502}
    assert entry.options == {
        "electric_power_sensor": "sensor.power",
        "scan_interval": 20,
        "slow_scan_interval": 400,
        "demo_mode": True,
    }
    assert entry.unique_id == "192.168.1.200:502"
    reload_mock.assert_awaited_once_with(entry.entry_id)


@pytest.mark.asyncio
async def test_config_flow_reconfigure_validation_error(
    hass, enable_custom_integrations
):
    """Test reconfigure flow with invalid input keeps the entry unchanged."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
        data={
            CONF_HOST: "invalid host with spaces",
            CONF_PORT: 502,
            "scan_interval": 20,
            "slow_scan_interval": 400,
            "demo_mode": False,
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"
    assert "errors" in result
    assert result["errors"][CONF_HOST] == "invalid_host"
    assert entry.data[CONF_HOST] == "192.168.1.100"
    assert entry.unique_id == "192.168.1.100:502"


@pytest.mark.asyncio
async def test_config_flow_reconfigure_connection_error(
    hass, enable_custom_integrations
):
    """Test reconfigure flow with connection error keeps the entry unchanged."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15},
    )
    entry.add_to_hass(hass)

    with mock.patch.object(
        RealModbusTcpClient,
        "create",
        new=mock.AsyncMock(return_value=_FakeModbusClient(connected=False)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={
                CONF_HOST: "192.168.1.200",
                CONF_PORT: 502,
                "scan_interval": 20,
                "slow_scan_interval": 400,
                "demo_mode": False,  # Not demo mode, so connection test runs
            },
        )

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"
    assert "errors" in result
    assert result["errors"][CONF_HOST] == "cannot_connect"
    assert entry.data[CONF_HOST] == "192.168.1.100"
    assert entry.unique_id == "192.168.1.100:502"


@pytest.mark.asyncio
async def test_config_flow_unique_id_prevents_duplicates(
    hass, enable_custom_integrations
):
    """Test that unique ID prevents duplicate entries."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
        options={"scan_interval": 15, "demo_mode": True},
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            "scan_interval": 15,
            "slow_scan_interval": 300,
            "demo_mode": True,
        },
    )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


def test_config_flow_registers_as_handler_for_domain():
    """Regression: the flow class must self-register as handler for DOMAIN.

    Home Assistant only registers config flow handlers when the flow class is
    declared with ``domain=<DOMAIN>`` (see ``ConfigFlow.__init_subclass__`` in
    ``homeassistant.config_entries``). Without registration, boot-time
    migration of a stored entry fails with "Flow handler not found for entry
    ..." and the entry is left in MIGRATION_ERROR state.
    """
    # Importing the module above registers the class in the HA handler registry.
    assert config_entries.HANDLERS.get(DOMAIN) is ConfigFlow

    # Entries stored by HA/the Docker demo test use version 1 / minor_version
    # 1; matching handler versions keep the boot-time migration a no-op.
    assert ConfigFlow.VERSION == 1
    assert ConfigFlow.MINOR_VERSION == 1
