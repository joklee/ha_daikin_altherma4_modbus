"""Performance tests for Daikin Altherma 4 Modbus integration."""

import pytest

from tests.fakes.modbus import FakeModbusClient


@pytest.mark.asyncio
async def test_batching_reduces_requests():
    """Test that batched register reads reduce the number of Modbus requests."""

    client = FakeModbusClient("192.168.1.100", 502, connected=True)

    # Read registers individually (67 separate requests)
    for addr in range(21, 88):
        await client.read_input_registers(addr, 1)

    assert client.read_count == 67, "Individual reads should make 67 requests"
    assert client.write_count == 0, "No writes should have occurred"
    assert client.operation_count == 67, "Total operations should be 67"

    # Reset counter
    client.reset()

    # Read registers in one batch (1 request)
    await client.read_input_registers(21, 67)

    assert client.read_count == 1, "Batch read should make only 1 request"
    assert client.write_count == 0, "No writes should have occurred"
    assert client.operation_count == 1, "Total operations should be 1"


@pytest.mark.asyncio
async def test_batching_returns_same_data():
    """Test that batched register reads return the same data as individual reads."""

    client = FakeModbusClient("192.168.1.100", 502, connected=True)

    # Read registers individually
    individual_results = []
    for addr in range(21, 88):
        result = await client.read_input_registers(addr, 1)
        individual_results.append(result)

    # Read registers in one batch
    batch_result = await client.read_input_registers(21, 67)

    # Compare data: each individual read should match the corresponding batch register
    for i, individual in enumerate(individual_results):
        addr = 21 + i
        # Extract the single register value from the individual read
        individual_value = individual.registers[addr]
        # Extract the corresponding register from the batch read
        batch_value = batch_result.registers[addr]
        assert individual_value == batch_value, (
            f"Register at address {addr} mismatch: {individual_value} != {batch_value}"
        )


@pytest.mark.asyncio
async def test_batching_reduces_modbus_requests_across_register_types():
    """Test that batching reduces requests across different register types."""

    # Test OLD implementation (multiple small reads)
    old_client = FakeModbusClient("192.168.1.100", 502)
    await old_client.connect()

    # OLD: 2 separate input register blocks
    await old_client.read_input_registers(21, 33)  # Block 1
    await old_client.read_input_registers(54, 34)  # Block 2

    # OLD: 3 separate holding register blocks
    await old_client.read_holding_registers(1, 25)  # Block 1
    await old_client.read_holding_registers(26, 25)  # Block 2
    await old_client.read_holding_registers(51, 30)  # Block 3

    old_operations = len(old_client.get_read_operations())

    # Test NEW implementation (optimized batching)
    new_client = FakeModbusClient("192.168.1.100", 502)
    await new_client.connect()

    # NEW: 1 single input register block
    await new_client.read_input_registers(21, 67)  # All in one!

    # NEW: 1 single holding register block
    await new_client.read_holding_registers(1, 79)  # All in one!

    new_operations = len(new_client.get_read_operations())

    # Verify improvements
    assert new_operations < old_operations, (
        f"New implementation should use fewer operations: {new_operations} < {old_operations}"
    )
    assert new_operations == 2, "New implementation should use exactly 2 operations"
    assert old_operations == 5, "Old implementation should use exactly 5 operations"
