"""Pytest fixtures for Modbus fakes."""

import pytest

from tests.fakes.modbus import FakeModbusClient


@pytest.fixture
def mock_client():
    """Mock Modbus TCP client."""
    return FakeModbusClient("192.168.1.100", 502)


@pytest.fixture
def connected_client():
    """Mock Modbus TCP client that starts connected."""
    client = FakeModbusClient("192.168.1.100", 502)
    client.connected = True
    return client


@pytest.fixture
def reset_client():
    """Return a factory for creating fresh FakeModbusClient instances."""

    def _factory(**kwargs):
        return FakeModbusClient(**kwargs)

    return _factory
