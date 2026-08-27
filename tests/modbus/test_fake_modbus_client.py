"""Tests for FakeModbusClient register read semantics.

These tests verify that FakeModbusClient correctly reproduces the semantics
of the real MockModbusResponse from mock_client.py, specifically that
register values are accessible via 1-based indexing on the response.
"""

import pytest

from tests.fakes.modbus import FakeModbusClient


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear demo data cache before each test."""
    FakeModbusClient.clear_demo_data_cache()
    yield


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
    response = await connected_client.read_discrete_inputs(1, 2)

    assert response.bits[1] is True
    assert response.bits[2] is False


@pytest.mark.asyncio
async def test_read_coils_returns_requested_values(connected_client):
    """Test that read_coils returns correct values at 1-based addresses."""
    response = await connected_client.read_coils(1, 2)

    assert response.bits[1] is True
    assert response.bits[2] is False


@pytest.mark.asyncio
async def test_write_single_register(connected_client):
    """Test writing a single holding register."""
    response = await connected_client.write_single_register(1, 1234)

    assert response.register_address == 1
    assert response.register_value == 1234


@pytest.mark.asyncio
async def test_write_single_coil(connected_client):
    """Test writing a single coil."""
    response = await connected_client.write_single_coil(1, True)

    assert response.output_address == 1
    assert response.output_value is True


@pytest.mark.asyncio
async def test_write_multiple_registers(connected_client):
    """Test writing multiple holding registers."""
    response = await connected_client.write_multiple_registers(1, [100, 200, 300])

    assert response.register_address == 1
    assert response.register_count == 3


@pytest.mark.asyncio
async def test_write_multiple_coils(connected_client):
    """Test writing multiple coils."""
    response = await connected_client.write_multiple_coils(1, [True, False, True])

    assert response.output_address == 1
    assert response.output_count == 3


@pytest.mark.asyncio
async def test_disconnect(connected_client):
    """Test disconnecting the client."""
    await connected_client.disconnect()
    assert connected_client.connected is False


@pytest.mark.asyncio
async def test_write_register_reports_no_error(connected_client):
    """A successful register write must report a successful (non-error) response.

    This guards the success/failure contract of the fake: callers must be able
    to distinguish a successful write from a failed one via ``isError()``.
    """
    response = await connected_client.write_register(1, 2500)
    assert response.isError() is False
    assert response.is_error() is False


@pytest.mark.asyncio
async def test_write_coil_reports_no_error(connected_client):
    """A successful coil write must report a successful response."""
    response = await connected_client.write_coil(1, True)
    assert response.isError() is False
    assert response.is_error() is False


@pytest.mark.asyncio
async def test_interface_alias_writes_report_no_error(connected_client):
    """The ModbusClientInterface-compatible aliases succeed without error."""
    reg_response = await connected_client.write_holding_register(1, 2500)
    assert reg_response.isError() is False

    coil_response = await connected_client.write_coil_register(1, True)
    assert coil_response.isError() is False


def test_demo_data_discrete_inputs_are_boolean():
    """Regression: generated demo discrete inputs must be boolean values.

    Previously the mock assigned non-boolean values for some discrete inputs,
    which broke binary_sensor semantics. Preserve the regression at the fake's
    unit-test boundary.
    """
    data = FakeModbusClient.generate_demo_register_data()
    discrete_inputs = data["discrete_inputs"]

    assert isinstance(discrete_inputs, list)
    assert len(discrete_inputs) > 0
    assert all(isinstance(value, bool) for value in discrete_inputs)
