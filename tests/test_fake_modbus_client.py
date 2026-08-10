"""Tests for FakeModbusClient register read semantics.

These tests verify that FakeModbusClient correctly reproduces the semantics
of the real MockModbusResponse from mock_client.py, specifically that
register values are accessible via 1-based indexing on the response.
"""

import pytest

from tests.fakes.modbus import FakeModbusClient


@pytest.fixture
def connected_client():
    """Create a connected FakeModbusClient."""
    client = FakeModbusClient("192.168.1.100", 502)
    client.connected = True
    return client


@pytest.mark.asyncio
async def test_read_input_registers_returns_requested_values(connected_client):
    """Test that read_input_registers returns correct values at 1-based addresses."""
    response = await connected_client.read_input_registers(1, 2)

    assert response.registers[1] == 3240
    assert response.registers[2] == 3045


@pytest.mark.asyncio
async def test_read_input_registers_at_offset(connected_client):
    """Test reading input registers at a non-zero address offset."""
    response = await connected_client.read_input_registers(40, 3)

    assert response.registers[40] == 3250
    assert response.registers[41] == 2750
    assert response.registers[42] == 2850


@pytest.mark.asyncio
async def test_read_holding_registers_returns_requested_values(connected_client):
    """Test that read_holding_registers returns correct values at 1-based addresses."""
    response = await connected_client.read_holding_registers(1, 2)

    assert response.registers[1] == 2500
    assert response.registers[2] == 1800


@pytest.mark.asyncio
async def test_read_discrete_inputs_returns_requested_values(connected_client):
    """Test that read_discrete_inputs returns correct values at 1-based addresses."""
    response = await connected_client.read_discrete_inputs(11, 1)

    assert response.bits[11] is True


@pytest.mark.asyncio
async def test_read_coils_returns_requested_values(connected_client):
    """Test that read_coils returns correct values at 1-based addresses."""
    response = await connected_client.read_coils(1, 2)

    assert response.bits[1] is True
    assert response.bits[2] is True
