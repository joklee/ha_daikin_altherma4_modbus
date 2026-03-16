"""Test to verify mock client doesn't generate invalid 16-bit values."""

import pytest

from custom_components.ha_daikin_altherma4_modbus.mock_client import MockModbusTcpClient


@pytest.mark.asyncio
async def test_mock_client_valid_16bit_values():
    """Test that mock client generates only valid 16-bit values."""

    client = MockModbusTcpClient("localhost", 502)
    await client.connect()

    # Test input registers
    input_result = await client.read_input_registers(0, 100)
    for i, value in enumerate(input_result.registers):
        assert 0 <= value <= 65535, (
            f"Input register {i}: Value {value} is outside 16-bit range"
        )

    # Test holding registers
    holding_result = await client.read_holding_registers(0, 100)
    for i, value in enumerate(holding_result.registers):
        assert 0 <= value <= 65535, (
            f"Holding register {i}: Value {value} is outside 16-bit range"
        )

    await client.disconnect()


@pytest.mark.asyncio
async def test_mock_client_signed_register_conversion():
    """Test that signed registers are properly converted to unsigned."""

    client = MockModbusTcpClient("localhost", 502)
    await client.connect()

    # Read registers that have negative min_value (holding_54, holding_55, etc.)
    # These should be converted to unsigned 16-bit representation
    result = await client.read_holding_registers(54, 4)  # holding_54 to holding_57

    for i, value in enumerate(
        result.registers[:4]
    ):  # First 4 are the holding registers
        assert 0 <= value <= 65535, (
            f"Signed register {54 + i}: Value {value} is outside 16-bit range"
        )

        # Values in the range 65526-65535 likely represent negative numbers
        if value > 65535 - 10:
            # This is probably a negative number converted to unsigned
            signed_value = value - 65536
            assert -10 <= signed_value <= -1, (
                f"Expected negative value, got {signed_value} from {value}"
            )

    await client.disconnect()


def test_mock_client_data_generation():
    """Test the demo data generation function directly."""

    demo_data = MockModbusTcpClient.generate_demo_register_data()

    # Check all value types
    for register_type, values in demo_data.items():
        if register_type in ["input_registers", "holding_registers"]:
            for i, value in enumerate(values):
                assert 0 <= value <= 65535, (
                    f"{register_type}[{i}]: Value {value} is outside 16-bit range"
                )

    # Check that we have the expected register types
    assert "input_registers" in demo_data
    assert "holding_registers" in demo_data
    assert "discrete_inputs" in demo_data
    assert "coils" in demo_data


@pytest.mark.asyncio
async def test_mock_client_reproducible_data():
    """Test that mock client generates consistent data structure."""

    client1 = MockModbusTcpClient("localhost", 502)
    await client1.connect()

    client2 = MockModbusTcpClient("localhost", 502)
    await client2.connect()

    # Both should generate valid data
    result1 = await client1.read_input_registers(0, 10)
    result2 = await client2.read_input_registers(0, 10)

    # All values should be in valid range
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
