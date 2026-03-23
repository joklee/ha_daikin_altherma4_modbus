"""Test for negative temperature value handling."""


def to_signed_16bit(value: int) -> int:
    """Convert unsigned 16-bit integer to signed integer."""
    if not (0 <= value <= 65535):
        return value
    if value >= 32768:
        return value - 65536
    return value


def to_unsigned_16bit(value: int) -> int:
    """Convert signed 16-bit integer to unsigned integer."""
    if value < 0:
        return value + 65536
    return value


def test_signed_16bit_conversion_negative_temperature():
    """Test that unsigned 16-bit values convert correctly to negative temperatures."""
    assert to_signed_16bit(65531) == -5
    assert to_signed_16bit(65535) == -1
    assert to_signed_16bit(65526) == -10
    assert to_signed_16bit(65036) == -500
    print("✓ All negative temperature conversions passed")


def test_signed_16bit_conversion_positive_temperature():
    """Test positive temperature values."""
    assert to_signed_16bit(1240) == 1240
    assert to_signed_16bit(0) == 0
    print("✓ All positive temperature conversions passed")


def test_mock_client_roundtrip():
    """Test the roundtrip: signed -> unsigned -> signed."""
    for original in [-6, -5, -1, 0, 1, 100]:
        unsigned = to_unsigned_16bit(original)
        signed_back = to_signed_16bit(unsigned)
        assert signed_back == original
    print("✓ Mock client round-trip conversions passed")


def test_temperature_scaling():
    """Test complete temperature conversion with scaling."""

    def convert_to_temperature(modbus_value, scale=0.01):
        signed = to_signed_16bit(modbus_value)
        return signed * scale

    assert convert_to_temperature(65036) == -5.0
    assert convert_to_temperature(1240) == 12.4
    print("✓ Temperature scaling conversions passed")


if __name__ == "__main__":
    test_signed_16bit_conversion_negative_temperature()
    test_signed_16bit_conversion_positive_temperature()
    test_mock_client_roundtrip()
    test_temperature_scaling()
    print("\n✓ All tests passed!")
