"""Retry utilities for Modbus operations."""

import asyncio
import logging
import random
from typing import Callable, TypeVar, Optional
from functools import wraps
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry operations."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_async(
    config: Optional[RetryConfig] = None, exceptions: tuple = (Exception,)
):
    """Decorator for async functions with retry logic.

    Args:
        config: Retry configuration
        exceptions: Tuple of exceptions to catch and retry on
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        _LOGGER.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts. "
                            f"Final error: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base**attempt),
                        config.max_delay,
                    )

                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= 0.5 + random.random() * 0.5

                    _LOGGER.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}). "
                        f"Retrying in {delay:.2f}s. Error: {e}"
                    )
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator


def add_jitter(base_interval: int, jitter_percent: float = 0.2) -> timedelta:
    """Add random jitter to prevent TCP bursts.

    Args:
        base_interval: Base interval in seconds
        jitter_percent: Percentage of jitter (default: 0.2 = 20%)

    Returns:
        timedelta: Interval with jitter applied
    """
    jitter_range = int(base_interval * jitter_percent)
    jitter = random.randint(-jitter_range, jitter_range)
    return timedelta(seconds=base_interval + jitter)


def add_exponential_jitter(
    base_interval: int, attempt: int, max_jitter: float = 0.5
) -> timedelta:
    """Add exponential jitter for retry operations.

    Args:
        base_interval: Base interval in seconds
        attempt: Current attempt number (0-based)
        max_jitter: Maximum jitter percentage (default: 0.5 = 50%)

    Returns:
        timedelta: Interval with exponential jitter applied
    """
    exponential_factor = min(2**attempt, 10)  # Cap at 10x
    jitter_range = int(base_interval * max_jitter)
    jitter = random.randint(-jitter_range, jitter_range)
    return timedelta(seconds=base_interval * exponential_factor + jitter)


# Default retry configurations
CONNECTION_RETRY = RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0)

READ_RETRY = RetryConfig(max_attempts=2, base_delay=0.5, max_delay=5.0)

WRITE_RETRY = RetryConfig(max_attempts=2, base_delay=1.0, max_delay=10.0)

# Default jitter configurations
DEFAULT_JITTER = 0.2  # 20% jitter for normal operations
RETRY_JITTER = 0.5  # 50% jitter for retry operations
