"""Tests for safe signed 16-bit integer conversions."""

from custom_components.ha_daikin_altherma4_modbus.common import (
    clamp_16bit,
    scaled_value_to_register,
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


class TestScaledValueToRegister:
    """Float-precision tests for scaled engineering value -> register."""

    def test_float_artefact_does_not_truncate(self):
        """x.xx / 0.01 can land just below the integer; int() truncates."""
        assert int(20.15 / 0.01) == 2014  # documents the old bug
        assert int(35.55 / 0.01) == 3554
        assert int(0.29 / 0.01) == 28
        assert scaled_value_to_register(20.15, 0.01) == 2015
        assert scaled_value_to_register(35.55, 0.01) == 3555
        assert scaled_value_to_register(0.29, 0.01) == 29
        assert scaled_value_to_register(48.29, 0.01) == 4829

    def test_typical_setpoints(self):
        assert scaled_value_to_register(20.0, 0.01) == 2000
        assert scaled_value_to_register(35.5, 0.01) == 3550
        assert scaled_value_to_register(55.0, 0.01) == 5500

    def test_negative_offsets(self):
        assert scaled_value_to_register(-3.5, 0.01) == -350
        assert scaled_value_to_register(-0.29, 0.01) == -29
        assert scaled_value_to_register(-10.0, 0.01) == -1000

    def test_power_limit_scale_0_001(self):
        assert scaled_value_to_register(3.5, 0.001) == 3500
        assert scaled_value_to_register(0.75, 0.001) == 750
        assert int(1.005 / 0.001) == 1004  # documents the old bug
        assert scaled_value_to_register(1.005, 0.001) == 1005

    def test_unity_and_zero_scale(self):
        assert scaled_value_to_register(42, 1) == 42
        assert scaled_value_to_register(42.4, 1) == 42
        assert scaled_value_to_register(42.6, 1) == 43
        # scale == 0 falls back to 1.0 instead of dividing by zero
        assert scaled_value_to_register(42.6, 0) == 43

    def test_boundary_values(self):
        assert scaled_value_to_register(0.0, 0.01) == 0
        assert scaled_value_to_register(327.67, 0.01) == 32767
        assert scaled_value_to_register(-327.68, 0.01) == -32768
