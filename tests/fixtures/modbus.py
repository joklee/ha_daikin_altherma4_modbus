"""Pytest fixtures for Modbus fakes."""

import pytest

from tests.fakes.modbus import FakeModbusClient


@pytest.fixture
def fake_modbus_client():
    """Create a FakeModbusClient instance."""
    return FakeModbusClient()


@pytest.fixture
def connected_modbus_client():
    """Create a connected FakeModbusClient instance."""
    client = FakeModbusClient()
    client.connected = True
    return client


@pytest.fixture
def disconnected_modbus_client():
    """Create a disconnected FakeModbusClient instance."""
    client = FakeModbusClient(connected=False)
    return client
