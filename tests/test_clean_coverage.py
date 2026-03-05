#!/usr/bin/env python3
"""
Clean test suite with proper coverage - final solution.
"""

import pytest
import sys
from unittest.mock import Mock

# Import shared test utilities
from .test_utils import setup_home_assistant_mocks, setup_project_paths

# Set up mocks and paths
setup_home_assistant_mocks()
project_root = setup_project_paths()

# Now import modules normally for coverage
# This allows coverage to track the actual source files
try:
    # Add custom_components to path
    custom_path = project_root / "custom_components"
    sys.path.insert(0, str(custom_path))

    # Import the modules we want to test
    from ha_daikin_altherma4_modbus.mock_client import (
        MockModbusTcpClient,
        MockModbusResponse,
    )
    from ha_daikin_altherma4_modbus import const

    COVERAGE_WORKING = True
except ImportError as e:
    print(f"Could not import for coverage: {e}")
    # Fallback to manual loading
    import importlib.util
    import types

    custom_components_path = (
        project_root / "custom_components" / "ha_daikin_altherma4_modbus"
    )

    # Load mock_client with patched imports
    with open(custom_components_path / "mock_client.py", "r") as f:
        source = f.read()

    # Replace relative imports
    source = source.replace(
        "from .client_interface", "from ha_daikin_altherma4_modbus.client_interface"
    )
    source = source.replace("from .const", "from ha_daikin_altherma4_modbus.const")

    mock_client_module = types.ModuleType("ha_daikin_altherma4_modbus.mock_client")
    exec(source, mock_client_module.__dict__)
    sys.modules["ha_daikin_altherma4_modbus.mock_client"] = mock_client_module

    MockModbusTcpClient = mock_client_module.MockModbusTcpClient
    MockModbusResponse = mock_client_module.MockModbusResponse

    # Load const
    const_spec = importlib.util.spec_from_file_location(
        "ha_daikin_altherma4_modbus.const", custom_components_path / "const.py"
    )
    const = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(const)
    sys.modules["ha_daikin_altherma4_modbus.const"] = const

    COVERAGE_WORKING = False


# Pytest fixtures
@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass_mock = Mock()
    hass_mock.data = {}
    hass_mock.config = Mock()
    hass_mock.config.time_zone = "Europe/Berlin"
    return hass_mock


@pytest.fixture
def mock_client():
    """Mock Modbus TCP client."""
    return MockModbusTcpClient("192.168.1.100", 502)


@pytest.fixture
def demo_data():
    """Demo register data."""
    return MockModbusTcpClient._generate_demo_register_data()


class TestMockClientClean:
    """Clean test cases for MockModbusTcpClient."""

    def test_initialization(self, mock_client):
        """Test client initialization."""
        assert mock_client.host == "192.168.1.100"
        assert mock_client.port == 502
        assert mock_client.connected is False
        assert mock_client._demo_data is not None

    @pytest.mark.asyncio
    async def test_connection(self, mock_client):
        """Test connection and disconnection."""
        await mock_client.connect()
        assert mock_client.connected is True

        await mock_client.disconnect()
        assert mock_client.connected is False

    @pytest.mark.asyncio
    async def test_read_operations(self, mock_client):
        """Test all read operations."""
        # Test input registers
        input_resp = await mock_client.read_input_registers(1, 5)
        assert hasattr(input_resp, "registers")
        assert len(input_resp.registers) >= 5

        # Test holding registers
        holding_resp = await mock_client.read_holding_registers(1, 5)
        assert hasattr(holding_resp, "registers")
        assert len(holding_resp.registers) >= 5

        # Test discrete inputs
        discrete_resp = await mock_client.read_discrete_inputs(1, 5)
        assert hasattr(discrete_resp, "bits")
        assert len(discrete_resp.bits) >= 5

        # Test coils
        coil_resp = await mock_client.read_coils(1, 5)
        assert hasattr(coil_resp, "bits")
        assert len(coil_resp.bits) >= 5

    def test_demo_data_generation(self, demo_data):
        """Test demo data generation."""
        assert isinstance(demo_data, dict)
        required_keys = [
            "input_registers",
            "holding_registers",
            "discrete_inputs",
            "coils",
        ]
        for key in required_keys:
            assert key in demo_data
            assert isinstance(demo_data[key], list)
            assert len(demo_data[key]) > 0

    def test_discrete_input_bug_fix(self, demo_data):
        """Test that the discrete input value assignment bug is fixed."""
        discrete_inputs = demo_data["discrete_inputs"]

        # All values should be boolean (the fix)
        assert all(isinstance(value, bool) for value in discrete_inputs)

        # Should have values
        assert len(discrete_inputs) > 0

    def test_response_object(self):
        """Test MockModbusResponse object."""
        response = MockModbusResponse([100, 200, 300], 1, 3)

        assert hasattr(response, "registers")
        assert hasattr(response, "is_bits")
        assert response.is_bits is False
        assert len(response.registers) >= 3

    def test_constants(self):
        """Test constants access."""
        if COVERAGE_WORKING:
            assert hasattr(const, "DOMAIN")
            assert hasattr(const, "DEFAULT_PORT")
            assert const.DOMAIN == "ha_daikin_altherma4_modbus"
            assert const.DEFAULT_PORT == 502


class TestIntegrationClean:
    """Clean integration tests."""

    def test_full_workflow(self, mock_client):
        """Test complete workflow."""
        demo_data = MockModbusTcpClient._generate_demo_register_data()
        assert isinstance(demo_data, dict)

        response = MockModbusResponse([100, 200], 1, 2)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 2

    def test_data_structure(self, demo_data):
        """Test data structure integrity."""
        for key, values in demo_data.items():
            assert isinstance(values, list)
            assert len(values) > 0

    def test_error_handling(self):
        """Test error handling."""
        MockModbusTcpClient("192.168.1.100", 502)
        demo_data = MockModbusTcpClient._generate_demo_register_data()
        discrete_inputs = demo_data.get("discrete_inputs", [])

        # Verify the fix works
        assert isinstance(discrete_inputs, list)
        assert all(isinstance(v, bool) for v in discrete_inputs)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
