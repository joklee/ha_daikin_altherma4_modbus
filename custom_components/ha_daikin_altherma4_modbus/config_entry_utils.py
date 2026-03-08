"""Shared helpers for reading Home Assistant config entry values."""


def entry_value(entry, key, default=None):
    """Read config value from options first, then fallback to data."""
    options = getattr(entry, "options", {}) or {}
    data = getattr(entry, "data", {}) or {}
    return options.get(key, data.get(key, default))


def entry_data_value(entry, key, default=None):
    """Read config value from entry data only."""
    data = getattr(entry, "data", {}) or {}
    return data.get(key, default)
