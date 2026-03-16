"""Test to reproduce and verify the data_description error in config flow."""

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def _install_common_homeassistant_stubs(monkeypatch):
    """Install common Home Assistant stubs."""
    # Mock homeassistant base module
    homeassistant = types.ModuleType("homeassistant")
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)

    # Mock homeassistant.config_entries
    config_entries_module = types.ModuleType("homeassistant.config_entries")
    config_entries_module.CONN_CLASS_LOCAL_POLL = "local_poll"

    class FakeConfigFlow:
        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__()

        def async_create_entry(self, title, data, options=None):
            return {
                "type": "create_entry",
                "title": title,
                "data": data,
                "options": options,
            }

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    class FakeOptionsFlow:
        def __init__(self, config_entry):
            self._config_entry = config_entry
            self.hass = SimpleNamespace(config_entries=SimpleNamespace())

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    config_entries_module.ConfigFlow = FakeConfigFlow
    config_entries_module.OptionsFlow = FakeOptionsFlow
    monkeypatch.setitem(
        sys.modules, "homeassistant.config_entries", config_entries_module
    )

    # Mock homeassistant.const
    const_module = types.ModuleType("homeassistant.const")
    const_module.CONF_HOST = "host"
    const_module.CONF_PORT = "port"
    monkeypatch.setitem(sys.modules, "homeassistant.const", const_module)

    # Mock voluptuous
    voluptuous_module = types.ModuleType("voluptuous")

    def _identity(value, default=None):
        return value

    class FakeSchema:
        def __init__(self, schema):
            self.schema = schema

        def __call__(self, value):
            return value

    voluptuous_module.Required = _identity
    voluptuous_module.Optional = _identity
    voluptuous_module.Schema = FakeSchema
    monkeypatch.setitem(sys.modules, "voluptuous", voluptuous_module)


def _load_config_flow_module(monkeypatch):
    """Load config flow module with mocked dependencies."""
    import importlib
    import tempfile

    _install_common_homeassistant_stubs(monkeypatch)

    package_name = "custom_components.ha_daikin_altherma4_modbus"
    package_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    package_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, package_name, package_module)

    # Mock const module
    const_name = f"{package_name}.const"
    const_module = types.ModuleType(const_name)
    const_module.DOMAIN = "ha_daikin_altherma4_modbus"
    const_module.SLOW_SCAN_INTERVAL = 600
    monkeypatch.setitem(sys.modules, const_name, const_module)

    # Mock init module with NORMAL_SCAN_INTERVAL
    init_name = f"{package_name}"
    init_module = types.ModuleType(init_name)
    init_module.NORMAL_SCAN_INTERVAL = 10
    monkeypatch.setitem(sys.modules, init_name, init_module)

    # Mock config entry utils
    config_entry_utils_name = f"{package_name}.config_entry_utils"
    config_entry_utils_module = types.ModuleType(config_entry_utils_name)

    def entry_value(entry, key, default=None):
        return entry.options.get(key, default)

    config_entry_utils_module.entry_value = entry_value
    monkeypatch.setitem(sys.modules, config_entry_utils_name, config_entry_utils_module)

    # Create the actual config_flow module by loading the real file
    config_flow_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
        / "config_flow.py"
    )

    # Read the file content and modify imports
    with open(config_flow_path, "r") as f:
        content = f.read()

    # Replace relative imports with absolute imports
    content = content.replace(
        "from . import NORMAL_SCAN_INTERVAL",
        f"from {package_name} import NORMAL_SCAN_INTERVAL",
    )
    content = content.replace(
        "from .config_entry_utils import entry_value",
        f"from {config_entry_utils_name} import entry_value",
    )
    content = content.replace(
        "from .const import DOMAIN, SLOW_SCAN_INTERVAL",
        f"from {const_name} import DOMAIN, SLOW_SCAN_INTERVAL",
    )

    # Create a temporary file with modified content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        # Load the modified config_flow module
        spec = importlib.util.spec_from_file_location("config_flow", tmp_file_path)
        config_flow_module = importlib.util.module_from_spec(spec)

        # Install it in sys.modules before loading
        module_name = f"{package_name}.config_flow"
        sys.modules[module_name] = config_flow_module

        # Load the module
        spec.loader.exec_module(config_flow_module)

        return config_flow_module
    finally:
        # Clean up temporary file
        import os

        os.unlink(tmp_file_path)


@pytest.mark.asyncio
async def test_config_flow_data_description_error(monkeypatch):
    """Test that reproduces the data_description parameter error."""
    config_flow_module = _load_config_flow_module(monkeypatch)

    # Create a ConfigFlow instance
    flow = config_flow_module.ConfigFlow()
    flow.hass = Mock()

    # Mock the step_user method to trigger async_show_form
    try:
        # This should trigger the data_description error
        result = await flow.async_step_user({})

        # If we get here, check if the result contains the error
        assert result["type"] == "form", "Expected form result"

        # The flow should succeed if data_description is handled correctly
        assert "step_id" in result
        assert result["step_id"] == "user"

    except TypeError as e:
        if "data_description" in str(e):
            pytest.fail(f"data_description parameter error detected: {e}")
        else:
            # Re-raise if it's a different TypeError
            raise


@pytest.mark.asyncio
async def test_config_flow_with_valid_data(monkeypatch):
    """Test config flow with valid user input."""
    config_flow_module = _load_config_flow_module(monkeypatch)

    flow = config_flow_module.ConfigFlow()
    flow.hass = Mock()

    # Mock user input
    user_input = {
        "host": "192.168.1.100",
        "port": 502,
        "scan_interval": 30,
        "slow_scan_interval": 300,
        "demo_mode": True,
    }

    try:
        result = await flow.async_step_user(user_input)

        # Should create entry if all data is valid
        if result["type"] == "create_entry":
            assert "title" in result
            assert "data" in result
        elif result["type"] == "form":
            # If form is returned, should not have data_description error
            assert "step_id" in result

    except TypeError as e:
        if "data_description" in str(e):
            pytest.fail(f"data_description parameter error detected: {e}")
        else:
            raise


@pytest.mark.asyncio
async def test_options_flow_data_description_error(monkeypatch):
    """Test options flow for data_description errors."""
    config_flow_module = _load_config_flow_module(monkeypatch)

    # Create a mock config entry
    config_entry = SimpleNamespace(
        entry_id="test_entry_1",
        data={"host": "192.168.1.100", "port": 502},
        options={
            "scan_interval": 30,
            "slow_scan_interval": 300,
            "demo_mode": True,
        },
    )

    # Create OptionsFlow instance
    options_flow = config_flow_module.OptionsFlow(config_entry)
    options_flow.hass = Mock()

    try:
        result = await options_flow.async_step_init(None)

        # Should return form without data_description error
        assert result["type"] == "form"
        assert "step_id" in result
        assert result["step_id"] == "init"

    except TypeError as e:
        if "data_description" in str(e):
            pytest.fail(
                f"data_description parameter error detected in options flow: {e}"
            )
        else:
            raise


@pytest.mark.asyncio
async def test_config_flow_form_structure(monkeypatch):
    """Test that config flow forms have the expected structure."""
    config_flow_module = _load_config_flow_module(monkeypatch)

    flow = config_flow_module.ConfigFlow()
    flow.hass = Mock()

    try:
        # Test initial form
        result = await flow.async_step_user({})

        assert result["type"] == "form"
        assert "data_schema" in result
        assert "step_id" in result

        # Check that data_description is NOT in the result (should be in strings.json)
        assert "data_description" not in result, (
            "data_description should not be in form result"
        )

        # Check that the form has the expected fields
        schema = result["data_schema"].schema

        expected_fields = [
            "host",
            "port",
            "scan_interval",
            "slow_scan_interval",
            "electric_power_sensor",
            "demo_mode",
        ]
        for field in expected_fields:
            assert field in str(schema), f"Missing field: {field}"

    except TypeError as e:
        if "data_description" in str(e):
            pytest.fail(f"data_description parameter error detected: {e}")
        else:
            raise
