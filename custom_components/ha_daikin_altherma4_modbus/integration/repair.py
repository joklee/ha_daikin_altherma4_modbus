"""Repair issue management for Daikin Altherma 4 Modbus integration."""

import inspect
import logging
import re
from contextlib import contextmanager

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity

from ..core.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Issue IDs
ISSUE_CONNECTION_LOST = "connection_lost"
ISSUE_DEVICE_ABNORMALITY = "device_abnormality"

# Home Assistant 2026.11 added config_entry_id and async_refresh_issues to the
# issue registry. Detect support so the integration keeps working on older
# releases while using the new APIs once they are available.
_SUPPORTS_CONFIG_ENTRY_ID = (
    "config_entry_id" in inspect.signature(ir.async_create_issue).parameters
)


def connection_issue_id(entry) -> str:
    """Return the connection-lost issue id for a config entry."""
    return f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}"


def abnormality_issue_id(entry) -> str:
    """Return the abnormality issue id for a config entry."""
    return f"{ISSUE_DEVICE_ABNORMALITY}_{entry.entry_id}"


def abnormality_issue_pattern(entry) -> str:
    """Return the refresh pattern matching a config entry's abnormality issue."""
    return f"^{re.escape(abnormality_issue_id(entry))}$"


def _create_issue(hass, entry, issue_id: str, **kwargs) -> None:
    """Create a repair issue, linked to the entry when supported."""
    if _SUPPORTS_CONFIG_ENTRY_ID:
        kwargs["config_entry_id"] = entry.entry_id
    ir.async_create_issue(hass, DOMAIN, issue_id, **kwargs)


@contextmanager
def async_refresh_issue_set(hass, entry, issue_id_pattern: str):
    """Refresh a set of repair issues when Home Assistant supports it.

    Yields ``True`` when the native 2026.11+ refresh API is active. Older
    releases yield ``False`` so callers can fall back to explicit deletes.
    """
    refresh = getattr(ir, "async_refresh_issues", None)
    if refresh is None:
        yield False
        return

    kwargs = {"issue_id_pattern": issue_id_pattern}
    if _SUPPORTS_CONFIG_ENTRY_ID:
        kwargs["config_entry_id"] = entry.entry_id
    with refresh(hass, DOMAIN, **kwargs):
        yield True


def async_create_connection_issue(hass, entry, error_message: str) -> None:
    """Create a repair issue for connection loss.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        error_message: Description of the connection error
    """
    issue_id = connection_issue_id(entry)
    _create_issue(
        hass,
        entry,
        issue_id,
        is_fixable=True,
        is_persistent=False,
        severity=IssueSeverity.ERROR,
        translation_key=ISSUE_CONNECTION_LOST,
        translation_placeholders={
            "entry_id": entry.entry_id,
            "entry_name": getattr(entry, "title", None) or entry.entry_id,
            "error_message": error_message,
        },
    )
    _LOGGER.warning("Created connection issue %s: %s", issue_id, error_message)


def async_delete_connection_issue(hass, entry) -> None:
    """Delete the connection repair issue for an entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    ir.async_delete_issue(hass, DOMAIN, connection_issue_id(entry))


def async_create_abnormality_issue(
    hass, entry, abnormality_code: str, abnormality_sub_code: int
) -> None:
    """Create a repair issue for device abnormality.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        abnormality_code: The abnormality code from the device
        abnormality_sub_code: The abnormality sub code from the device
    """
    issue_id = abnormality_issue_id(entry)
    _create_issue(
        hass,
        entry,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.WARNING,
        translation_key=ISSUE_DEVICE_ABNORMALITY,
        translation_placeholders={
            "entry_id": entry.entry_id,
            "entry_name": getattr(entry, "title", None) or entry.entry_id,
            "abnormality_code": str(abnormality_code),
            "abnormality_sub_code": str(abnormality_sub_code),
        },
    )
    _LOGGER.warning(
        "Created abnormality issue %s: code=%s sub_code=%d",
        issue_id,
        abnormality_code,
        abnormality_sub_code,
    )


def async_delete_abnormality_issue(hass, entry) -> None:
    """Delete the abnormality repair issue for an entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    ir.async_delete_issue(hass, DOMAIN, abnormality_issue_id(entry))
