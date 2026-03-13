"""Tests for safe signed 16-bit integer conversions."""

import sys
from pathlib import Path

# Add paths before importing modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(
    0, str(project_root / "custom_components" / "ha_daikin_altherma4_modbus")
)

from custom_components.ha_daikin_altherma4_modbus.common import (  # noqa: E402
    clamp_16bit,
    to_signed_16bit,
    to_unsigned_16bit,
)


class TestSigned16BitConversion:
    """Test safe 16-bit integer conversions."""

    def test_to_signed_16bit_positive_values(self):
        """Test conversion of positive values."""
        assert to_signed_16bit(0) == 0
        assert to_signed_16bit(1) == 1
        assert to_signed_16bit(32767) == 32767

    def test_to_signed_16bit_negative_values(self):
        """Test conversion of negative values (2's complement)."""
        assert to_signed_16bit(65535) == -1
        assert to_signed_16bit(65534) == -2
        assert to_signed_16bit(32768) == -32768

    def test_to_signed_16bit_boundary_values(self):
        """Test boundary values."""
        assert to_signed_16bit(32767) == 32767  # Max positive
        assert to_signed_16bit(32768) == -32768  # Min negative

    def test_to_signed_16bit_out_of_range(self):
        """Test values outside 16-bit range."""
        # Should log warning but return value
        assert to_signed_16bit(-1) == -1
        assert to_signed_16bit(65536) == 65536

    def test_to_unsigned_16bit_positive_values(self):
        """Test conversion of positive values."""
        assert to_unsigned_16bit(0) == 0
        assert to_unsigned_16bit(1) == 1
        assert to_unsigned_16bit(32767) == 32767

    def test_to_unsigned_16bit_negative_values(self):
        """Test conversion of negative values to 2's complement."""
        assert to_unsigned_16bit(-1) == 65535
        assert to_unsigned_16bit(-2) == 65534
        assert to_unsigned_16bit(-32768) == 32768

    def test_to_unsigned_16bit_boundary_values(self):
        """Test boundary values."""
        assert to_unsigned_16bit(32767) == 32767  # Max positive
        assert to_unsigned_16bit(-32768) == 32768  # Min negative

    def test_to_unsigned_16bit_out_of_range(self):
        """Test values outside signed 16-bit range."""
        # Should log warning but return value
        assert to_unsigned_16bit(-32769) == -32769
        assert to_unsigned_16bit(32768) == 32768

    def test_roundtrip_conversion(self):
        """Test that converting back and forth preserves values."""
        # Test positive values
        for i in [0, 1, 100, 32767]:
            assert to_unsigned_16bit(to_signed_16bit(i)) == i

        # Test negative values
        for signed_val in [-1, -100, -32768]:
            unsigned_val = to_unsigned_16bit(signed_val)
            assert to_signed_16bit(unsigned_val) == signed_val

    def test_clamp_16bit(self):
        """Test clamping to 16-bit range."""
        assert clamp_16bit(0) == 0
        assert clamp_16bit(32767) == 32767
        assert clamp_16bit(65535) == 65535

        assert clamp_16bit(-1) == 0
        assert clamp_16bit(-100) == 0
        assert clamp_16bit(65536) == 65535
        assert clamp_16bit(70000) == 65535


class TestRealWorldScenarios:
    """Test real-world Modbus scenarios."""

    def test_temperature_conversion(self):
        """Test typical temperature sensor values."""
        # Simulate Modbus register readings
        modbus_values = [65535, 65520, 32768, 100, 0, 32767]
        expected_temps = [-1, -16, -32768, 100, 0, 32767]

        for modbus_val, expected_temp in zip(modbus_values, expected_temps):
            actual_temp = to_signed_16bit(modbus_val)
            assert actual_temp == expected_temp

    def test_setpoint_conversion(self):
        """Test setpoint value conversion for writing."""
        # User wants to set -5°C
        user_value = -5
        expected_modbus = to_unsigned_16bit(user_value)

        # Should be 65531 (2's complement of -5)
        assert expected_modbus == 65531

        # Converting back should give original value
        assert to_signed_16bit(expected_modbus) == user_value

    def test_edge_case_values(self):
        """Test edge case values that commonly cause issues."""
        # Test all boundary conditions
        edge_cases = [
            (0, 0),  # Zero
            (1, 1),  # Minimum positive
            (32767, 32767),  # Max positive
            (32768, -32768),  # Min negative
            (65534, -2),  # Second most negative
            (65535, -1),  # Most negative
        ]

        for unsigned_val, expected_signed in edge_cases:
            result = to_signed_16bit(unsigned_val)
            assert result == expected_signed, f"Failed for {unsigned_val}"

            # Test reverse conversion
            reverse_result = to_unsigned_16bit(expected_signed)
            assert reverse_result == unsigned_val, (
                f"Reverse failed for {expected_signed}"
            )
