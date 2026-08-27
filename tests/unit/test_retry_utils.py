"""Tests for retry_utils.py."""

from datetime import timedelta

from custom_components.ha_daikin_altherma4_modbus.core.retry_utils import (
    CONNECTION_RETRY,
    DEFAULT_JITTER,
    READ_RETRY,
    RETRY_JITTER,
    WRITE_RETRY,
    RetryConfig,
    add_exponential_jitter,
    add_jitter,
)


def test_retry_config_defaults():
    """Test RetryConfig default values."""
    config = RetryConfig()
    assert config.max_attempts == 3
    assert config.base_delay == 1.0
    assert config.max_delay == 30.0
    assert config.exponential_base == 2.0
    assert config.jitter is True


def test_retry_config_custom():
    """Test RetryConfig with custom values."""
    config = RetryConfig(max_attempts=5, base_delay=2.0, max_delay=60.0)
    assert config.max_attempts == 5
    assert config.base_delay == 2.0
    assert config.max_delay == 60.0


def test_add_jitter_basic():
    """Test add_jitter returns timedelta within expected range."""
    base = 10
    result = add_jitter(base, jitter_percent=0.2)
    assert isinstance(result, timedelta)
    # Jitter range is ±20% of 10 = ±2 seconds
    assert 8 <= result.total_seconds() <= 12


def test_add_jitter_zero_percent():
    """Test add_jitter with 0% jitter returns exact base."""
    result = add_jitter(10, jitter_percent=0.0)
    assert result.total_seconds() == 10


def test_add_exponential_jitter():
    """Test add_exponential_jitter returns timedelta."""
    result = add_exponential_jitter(10, attempt=0)
    assert isinstance(result, timedelta)
    # Should be base * 1 + jitter
    assert result.total_seconds() >= 5  # 10 * 1 - 5 (50% jitter)


def test_add_exponential_jitter_scales():
    """Test add_exponential_jitter scales with attempt."""
    result0 = add_exponential_jitter(10, attempt=0)
    result1 = add_exponential_jitter(10, attempt=1)
    # Exponential factor caps at 10x
    assert result1.total_seconds() >= result0.total_seconds()


def test_default_constants():
    """Test default retry constants are defined."""
    assert CONNECTION_RETRY.max_attempts == 3
    assert READ_RETRY.max_attempts == 2
    assert WRITE_RETRY.max_attempts == 2
    assert DEFAULT_JITTER == 0.2
    assert RETRY_JITTER == 0.5
