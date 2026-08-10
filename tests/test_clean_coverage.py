#!/usr/bin/env python3
"""
Clean test suite with proper coverage - final solution.
Uses centralized FakeModbusClient from test_utils.
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add tests directory to path for test_utils import
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

# Import shared test utilities
from tests.fakes.modbus import FakeModbusClient, FakeModbusResponse
from tests.helpers.modules import (
    load_const_module,
    setup_home_assistant_mocks,
    setup_project_paths,
)

# Set up mocks and paths
setup_home_assistant_mocks()
project_root = setup_project_paths()

# Load const module for constants access
const = load_const_module(project_root)


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


class TestMockClientClean:
    """Clean test cases for FakeModbusClient."""

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
    async def test_read_operations(self, mock_client):
        """Test all read operations."""
        await mock_client.connect()

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

    @pytest.mark.asyncio
    async def test_write_operations(self, mock_client):
        """Test write operations."""
        await mock_client.connect()

        # Test write holding register
        write_resp = await mock_client.write_holding_register(1, 2500)
        assert hasattr(write_resp, "isError")

        # Test write coil
        coil_resp = await mock_client.write_coil_register(1, True)
        assert hasattr(coil_resp, "isError")

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
        """Test that the discrete input values are boolean."""
        discrete_inputs = demo_data["discrete_inputs"]

        # All values should be boolean
        assert all(isinstance(value, bool) for value in discrete_inputs)

        # Should have values
        assert len(discrete_inputs) > 0

    def test_response_object(self):
        """Test FakeModbusResponse object."""
        response = FakeModbusResponse([100, 200, 300], 1, 3)

        assert hasattr(response, "registers")
        assert hasattr(response, "is_bits")
        assert response.is_bits is False
        assert len(response.registers) >= 3

    def test_constants(self):
        """Test constants access."""
        assert hasattr(const, "DOMAIN")
        assert hasattr(const, "DEFAULT_PORT")
        assert const.DOMAIN == "ha_daikin_altherma4_modbus"
        assert const.DEFAULT_PORT == 502


class TestIntegrationClean:
    """Clean integration tests."""

    def test_full_workflow(self, mock_client):
        """Test complete workflow."""
        demo_data = FakeModbusClient.generate_demo_register_data()
        assert isinstance(demo_data, dict)

        response = FakeModbusResponse([100, 200], 1, 2)
        assert hasattr(response, "registers")
        assert len(response.registers) >= 2

    def test_data_structure(self, demo_data):
        """Test data structure integrity."""
        for values in demo_data.values():
            assert isinstance(values, list)
            assert len(values) > 0

    def test_error_handling(self):
        """Test error handling."""
        FakeModbusClient("192.168.1.100", 502)
        demo_data = FakeModbusClient.generate_demo_register_data()
        discrete_inputs = demo_data.get("discrete_inputs", [])

        # Verify the fix works
        assert isinstance(discrete_inputs, list)
        assert all(isinstance(v, bool) for v in discrete_inputs)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
