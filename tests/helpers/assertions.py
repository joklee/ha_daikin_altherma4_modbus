"""Assertion helpers for tests."""

from datetime import datetime, timezone


def create_test_trigger_time():
    """Create a consistent test trigger time."""
    return datetime(2024, 3, 2, 20, 30, 0, tzinfo=timezone.utc)


def assert_connected_once(client):
    """Assert that connect was called exactly once."""
    client.assert_called_once()


def assert_not_connected(client):
    """Assert that close was not called."""
    client.assert_not_called()
