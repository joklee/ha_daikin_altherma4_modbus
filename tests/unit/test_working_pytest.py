"""
Working pytest-compatible test suite for Daikin Altherma 4 Modbus integration.
Uses centralized FakeModbusClient from test_utils.
"""

from unittest.mock import Mock

import pytest

# Import shared test utilities
from tests.fakes.modbus import FakeModbusClient, FakeModbusResponse
from tests.helpers.modules import (
    load_const_module,
    setup_project_paths,
)

# Set up paths
project_root = setup_project_paths()

# Load const module for constants access
const_module = load_const_module(project_root)


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
    return FakeModbusClient("192.168.1.100", 502)


@pytest.fixture
def demo_data():
    """Demo register data."""
    return FakeModbusClient.generate_demo_register_data()


class TestMockClient:
    """Test cases for FakeModbusClient."""

    def test_initialization(self, mock_client):
        """Test client initialization."""
        assert mock_client.host == "192.168.1.100"
        assert mock_client.port == 502
        assert mock_client.connected is False

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
        await mock_client.connect()
        response = await mock_client.read_input_registers(1, 5)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 5

    @pytest.mark.asyncio
    async def test_read_holding_registers(self, mock_client):
        """Test reading holding registers."""
        await mock_client.connect()
        response = await mock_client.read_holding_registers(1, 5)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 5

    @pytest.mark.asyncio
    async def test_read_discrete_inputs(self, mock_client):
        """Test reading discrete inputs."""
        await mock_client.connect()
        response = await mock_client.read_discrete_inputs(1, 5)
        assert hasattr(response, "bits")
        assert len(response.bits) >= 5

    @pytest.mark.asyncio
    async def test_read_coils(self, mock_client):
        """Test reading coils."""
        await mock_client.connect()
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
        """Test FakeModbusResponse object."""
        response = FakeModbusResponse([100, 200, 300], 1, 3)

        # Check that response has expected attributes
        assert hasattr(response, "registers")
        assert hasattr(response, "is_bits")

        # Check basic properties
        assert response.is_bits is False
        assert len(response.registers) >= 3

    def test_constants_access(self):
        """Test that constants are accessible."""
        assert hasattr(const_module, "DOMAIN")
        assert hasattr(const_module, "DEFAULT_PORT")
        assert const_module.DOMAIN == "ha_daikin_altherma4_modbus"
        assert const_module.DEFAULT_PORT == 502


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, mock_client):
        """Test complete workflow."""
        # Test data generation
        demo_data = FakeModbusClient.generate_demo_register_data()
        assert isinstance(demo_data, dict)

        # Test response creation
        response = FakeModbusResponse([100, 200], 1, 2)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 2

    def test_data_structure(self, demo_data):
        """Test data structure integrity."""
        for values in demo_data.values():
            assert isinstance(values, list)
            assert len(values) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
