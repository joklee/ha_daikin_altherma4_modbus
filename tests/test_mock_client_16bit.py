"""Test to verify mock client doesn't generate invalid 16-bit values."""

import importlib
import sys
import types
from pathlib import Path

import pytest

# Add tests directory to path for test_utils import
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))


def _ensure_homeassistant_stubs():
    """Ensure homeassistant stubs are available and correctly configured.

    Does NOT remove existing stubs (which are set up by conftest.py) to avoid
    breaking other tests that rely on the conftest stubs.
    """
    if "homeassistant" not in sys.modules:
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.__path__ = []
        sys.modules["homeassistant"] = homeassistant
    else:
        homeassistant = sys.modules["homeassistant"]

    if "homeassistant.exceptions" not in sys.modules:
        exceptions_module = types.ModuleType("homeassistant.exceptions")
        exceptions_module.ConfigEntryNotReady = Exception
        sys.modules["homeassistant.exceptions"] = exceptions_module
        homeassistant.exceptions = exceptions_module

    if "homeassistant.const" not in sys.modules:
        const_module = types.ModuleType("homeassistant.const")
        const_module.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
        sys.modules["homeassistant.const"] = const_module
        homeassistant.const = const_module

    if "homeassistant.core" not in sys.modules:
        core_module = types.ModuleType("homeassistant.core")
        core_module.Event = object
        core_module.HomeAssistant = object
        sys.modules["homeassistant.core"] = core_module
        homeassistant.core = core_module

    if "homeassistant.helpers" not in sys.modules:
        helpers_module = types.ModuleType("homeassistant.helpers")
        helpers_module.__path__ = []
        sys.modules["homeassistant.helpers"] = helpers_module
        homeassistant.helpers = helpers_module

    if "homeassistant.helpers.update_coordinator" not in sys.modules:
        update_coordinator_module = types.ModuleType(
            "homeassistant.helpers.update_coordinator"
        )
        update_coordinator_module.DataUpdateCoordinator = object
        update_coordinator_module.CoordinatorEntity = object
        update_coordinator_module.UpdateFailed = Exception
        sys.modules["homeassistant.helpers.update_coordinator"] = (
            update_coordinator_module
        )

    if "homeassistant.helpers.typing" not in sys.modules:
        helpers_typing_module = types.ModuleType("homeassistant.helpers.typing")
        helpers_typing_module.ConfigType = dict
        sys.modules["homeassistant.helpers.typing"] = helpers_typing_module

    if "homeassistant.helpers.issue_registry" not in sys.modules:
        issue_registry_module = types.ModuleType("homeassistant.helpers.issue_registry")
        issue_registry_module.IssueSeverity = types.SimpleNamespace(
            ERROR="error", WARNING="warning"
        )
        issue_registry_module.async_create_issue = lambda *a, **kw: None
        issue_registry_module.async_delete_issue = lambda *a, **kw: None
        sys.modules["homeassistant.helpers.issue_registry"] = issue_registry_module

    if "homeassistant.helpers.restore_state" not in sys.modules:
        restore_state_module = types.ModuleType("homeassistant.helpers.restore_state")
        sys.modules["homeassistant.helpers.restore_state"] = restore_state_module


def _is_register_constants_polluted() -> bool:
    """Check if register_constants module is polluted by another test file.

    test_services.py replaces the real register_constants module with mock
    data using MockRegister objects that lack an 'address' attribute, or
    sets INPUT_REGISTERS to an empty list.

    Returns:
        True if the module is polluted, False otherwise.
    """
    rc_name = "custom_components.ha_daikin_altherma4_modbus.register_constants"
    rc_module = sys.modules.get(rc_name)
    if rc_module is None:
        return False

    registers = getattr(rc_module, "INPUT_REGISTERS", None)
    if registers is None:
        return True

    if len(registers) == 0:
        return True

    for reg in registers:
        if not hasattr(reg, "address"):
            return True
        if isinstance(reg, dict):
            return True

    return False


def _get_mock_client_class(monkeypatch):
    """Get MockModbusTcpClient class, restoring real register data first.

    If register_constants has been polluted by another test file (e.g.,
    test_services.py), this function restores the real register data
    into the existing module so that the mock_client can function correctly
    without breaking other tests that reference the module.

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        MockModbusTcpClient class
    """
    _ensure_homeassistant_stubs()

    if _is_register_constants_polluted():
        _restore_real_register_constants(monkeypatch)

    mock_client_name = "custom_components.ha_daikin_altherma4_modbus.mock_client"
    if mock_client_name not in sys.modules:
        importlib.import_module(mock_client_name)

    mock_client_module = sys.modules[mock_client_name]
    return mock_client_module.MockModbusTcpClient


def _restore_real_register_constants(monkeypatch):
    """Restore real register_constants data into the polluted module.

    test_services.py replaces the real register_constants module with mock
    data. This function loads the real register_constants module using the
    shared test_utils helper and copies the essential register lists into
    the polluted module. monkeypatch ensures the polluted values are restored
    after the test.

    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    from pathlib import Path

    from test_utils import load_register_constants_module

    project_root = Path(__file__).parent.parent
    real_rc = load_register_constants_module(project_root)

    rc_module = sys.modules[
        "custom_components.ha_daikin_altherma4_modbus.register_constants"
    ]
    for attr in [
        "INPUT_REGISTERS",
        "HOLDING_REGISTERS",
        "DISCRETE_REGISTERS",
        "COIL_REGISTERS",
        "CALCULATED_SENSORS",
    ]:
        if hasattr(real_rc, attr):
            monkeypatch.setattr(rc_module, attr, getattr(real_rc, attr))


# Setup stubs immediately
_ensure_homeassistant_stubs()


@pytest.mark.asyncio
async def test_mock_client_valid_16bit_values(monkeypatch):
    """Test that mock client generates only valid 16-bit values."""
    MockModbusTcpClient = _get_mock_client_class(monkeypatch)

    client = MockModbusTcpClient("localhost", 502)
    await client.connect()

    input_result = await client.read_input_registers(0, 100)
    for i, value in enumerate(input_result.registers):
        assert 0 <= value <= 65535, (
            f"Input register {i}: Value {value} is outside 16-bit range"
        )

    holding_result = await client.read_holding_registers(0, 100)
    for i, value in enumerate(holding_result.registers):
        assert 0 <= value <= 65535, (
            f"Holding register {i}: Value {value} is outside 16-bit range"
        )

    await client.disconnect()


@pytest.mark.asyncio
async def test_mock_client_signed_register_conversion(monkeypatch):
    """Test that signed registers are properly converted to unsigned."""
    MockModbusTcpClient = _get_mock_client_class(monkeypatch)

    client = MockModbusTcpClient("localhost", 502)
    await client.connect()

    result = await client.read_holding_registers(54, 4)

    for i, value in enumerate(result.registers[:4]):
        assert 0 <= value <= 65535, (
            f"Signed register {54 + i}: Value {value} is outside 16-bit range"
        )

        if value > 65535 - 10:
            signed_value = value - 65536
            assert -10 <= signed_value <= -1, (
                f"Expected negative value, got {signed_value} from {value}"
            )

    await client.disconnect()


def test_mock_client_data_generation(monkeypatch):
    """Test the demo data generation function directly."""
    MockModbusTcpClient = _get_mock_client_class(monkeypatch)

    demo_data = MockModbusTcpClient.generate_demo_register_data()

    for register_type, values in demo_data.items():
        if register_type in ["input_registers", "holding_registers"]:
            for i, value in enumerate(values):
                assert 0 <= value <= 65535, (
                    f"{register_type}[{i}]: Value {value} is outside 16-bit range"
                )

    assert "input_registers" in demo_data
    assert "holding_registers" in demo_data
    assert "discrete_inputs" in demo_data
    assert "coils" in demo_data


@pytest.mark.asyncio
async def test_mock_client_reproducible_data(monkeypatch):
    """Test that mock client generates consistent data structure."""
    MockModbusTcpClient = _get_mock_client_class(monkeypatch)

    client1 = MockModbusTcpClient("localhost", 502)
    await client1.connect()

    client2 = MockModbusTcpClient("localhost", 502)
    await client2.connect()

    result1 = await client1.read_input_registers(0, 10)
    result2 = await client2.read_input_registers(0, 10)

    for i, value in enumerate(result1.registers):
        assert 0 <= value <= 65535, (
            f"Client1 register {i}: Value {value} is outside 16-bit range"
        )

    for i, value in enumerate(result2.registers):
        assert 0 <= value <= 65535, (
            f"Client2 register {i}: Value {value} is outside 16-bit range"
        )

    await client1.disconnect()
    await client2.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
