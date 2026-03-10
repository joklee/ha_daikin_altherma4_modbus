#!/usr/bin/env python3
"""
Working pytest-compatible test suite for Daikin Altherma 4 Modbus integration.
"""

import sys
import types
from unittest.mock import Mock

import pytest

# Import shared test utilities
from .test_utils import setup_home_assistant_mocks, setup_project_paths

# Set up mocks and paths
setup_home_assistant_mocks()
project_root = setup_project_paths()

# Add custom components path
custom_components_path = (
    project_root / "custom_components" / "ha_daikin_altherma4_modbus"
)
sys.path.insert(0, str(custom_components_path))

# Create package structure
package = types.ModuleType("ha_daikin_altherma4_modbus")
sys.modules["ha_daikin_altherma4_modbus"] = package


# Load modules manually to handle relative imports
def load_module(module_name, file_path):
    """Load a module and handle its dependencies."""
    spec = None
    try:
        spec = __import__(module_name).__spec__ if module_name in sys.modules else None
    except ImportError:
        pass

    if spec is None:
        with open(file_path, "r") as f:
            source = f.read()

        # Replace relative imports
        source = source.replace("from .", "from ha_daikin_altherma4_modbus.")
        source = source.replace("import .", "import ha_daikin_altherma4_modbus.")

        module = types.ModuleType(module_name)
        exec(source, module.__dict__)
        sys.modules[f"ha_daikin_altherma4_modbus.{module_name}"] = module
        package.__dict__[module_name] = module
        return module

    return sys.modules[module_name]


# Load required modules
const_module = load_module("const", custom_components_path / "const.py")
client_interface_module = load_module(
    "client_interface", custom_components_path / "client_interface.py"
)
mock_client_module = load_module(
    "mock_client", custom_components_path / "mock_client.py"
)


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
    return mock_client_module.MockModbusTcpClient("192.168.1.100", 502)


@pytest.fixture
def demo_data():
    """Demo register data."""
    return mock_client_module.MockModbusTcpClient.generate_demo_register_data()


class TestMockClient:
    """Test cases for MockModbusTcpClient."""

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
    async def test_read_input_registers(self, mock_client):
        """Test reading input registers."""
        response = await mock_client.read_input_registers(1, 5)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 5

    @pytest.mark.asyncio
    async def test_read_holding_registers(self, mock_client):
        """Test reading holding registers."""
        response = await mock_client.read_holding_registers(1, 5)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 5

    @pytest.mark.asyncio
    async def test_read_discrete_inputs(self, mock_client):
        """Test reading discrete inputs."""
        response = await mock_client.read_discrete_inputs(1, 5)
        assert hasattr(response, "bits")
        assert len(response.bits) >= 5

    @pytest.mark.asyncio
    async def test_read_coils(self, mock_client):
        """Test reading coils."""
        response = await mock_client.read_coils(1, 5)
        assert hasattr(response, "bits")
        assert len(response.bits) >= 5

    def test_demo_data_generation(self, demo_data):
        """Test demo data generation."""
        assert isinstance(demo_data, dict)
        assert "input_registers" in demo_data
        assert "holding_registers" in demo_data
        assert "discrete_inputs" in demo_data
        assert "coils" in demo_data

    def test_discrete_input_bug_fix(self, demo_data):
        """Test that the discrete input value assignment bug is fixed."""
        discrete_inputs = demo_data["discrete_inputs"]

        # All values should be boolean
        assert all(isinstance(value, bool) for value in discrete_inputs)

        # Should have the expected number of values
        assert len(discrete_inputs) > 0

    def test_response_object(self):
        """Test MockModbusResponse object."""
        response = mock_client_module.MockModbusResponse([100, 200, 300], 1, 3)

        # Check that response has expected attributes
        assert hasattr(response, "registers")
        assert hasattr(response, "is_bits")

        # Check basic properties
        assert response.is_bits is False
        assert len(response.registers) >= 3


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, mock_client):
        """Test complete workflow."""
        # Test data generation
        demo_data = mock_client_module.MockModbusTcpClient.generate_demo_register_data()
        assert isinstance(demo_data, dict)

        # Test response creation
        response = mock_client_module.MockModbusResponse([100, 200], 1, 2)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 2

    def test_data_structure(self, demo_data):
        """Test data structure integrity."""
        for key, values in demo_data.items():
            assert isinstance(values, list)
            assert len(values) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
