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
    retry_async,
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


def _fast_config(**overrides):
    kwargs = {"max_attempts": 3, "base_delay": 0.001, "max_delay": 0.01}
    kwargs.update(overrides)
    return RetryConfig(jitter=False, **kwargs)


async def test_retry_async_succeeds_first_try():
    """A healthy function is returned without retries."""
    calls = []

    async def flaky():
        calls.append(1)
        return "ok"

    decorator = await retry_async(_fast_config(), (ValueError,))
    assert await decorator(flaky)() == "ok"
    assert len(calls) == 1


async def test_retry_async_recovers_after_failures():
    """Transient failures are retried until success."""
    calls = []

    async def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("boom")
        return "recovered"

    decorator = await retry_async(_fast_config(), (ValueError,))
    assert await decorator(flaky)() == "recovered"
    assert len(calls) == 3


async def test_retry_async_raises_after_exhaustion():
    """Exhausted attempts re-raise the last error."""
    import pytest

    async def always_fails():
        raise ValueError("persistent")

    decorator = await retry_async(_fast_config(max_attempts=2), (ValueError,))
    with pytest.raises(ValueError, match="persistent"):
        await decorator(always_fails)()


async def test_retry_async_ignores_unmatched_exceptions():
    """Exceptions outside the retry tuple propagate immediately."""
    import pytest

    calls = []

    async def flaky():
        calls.append(1)
        raise TypeError("not retried")

    decorator = await retry_async(_fast_config(), (ValueError,))
    with pytest.raises(TypeError):
        await decorator(flaky)()
    assert len(calls) == 1


async def test_retry_async_uses_default_config():
    """Omitting the config falls back to RetryConfig defaults."""

    async def healthy():
        return 42

    decorator = await retry_async()
    assert await decorator(healthy)() == 42
