"""Repair issue management for Daikin Altherma 4 Modbus integration."""

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
ISSUE_UNSUPPORTED_TEMPERATURE_UNIT = "unsupported_temperature_unit"


def connection_issue_id(entry) -> str:
    """Return the connection-lost issue id for a config entry."""
    return f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}"


def abnormality_issue_id(entry) -> str:
    """Return the abnormality issue id for a config entry."""
    return f"{ISSUE_DEVICE_ABNORMALITY}_{entry.entry_id}"


def unsupported_temperature_unit_issue_id(entry) -> str:
    """Return the unsupported-unit issue id for a config entry."""
    return f"{ISSUE_UNSUPPORTED_TEMPERATURE_UNIT}_{entry.entry_id}"


def abnormality_issue_pattern(entry) -> str:
    """Return the refresh pattern matching a config entry's abnormality issue."""
    return f"^{re.escape(abnormality_issue_id(entry))}$"


def _create_issue(hass, entry, issue_id: str, **kwargs) -> None:
    """Create a repair issue, linked to the config entry."""
    ir.async_create_issue(
        hass, DOMAIN, issue_id, config_entry_id=entry.entry_id, **kwargs
    )


@contextmanager
def async_refresh_issue_set(hass, entry, issue_id_pattern: str):
    """Refresh a set of repair issues via the HA 2026.11+ refresh API.

    Issues matching the pattern are deleted when they are not recreated
    inside the context.

    The scope is the pattern alone, deliberately without ``config_entry_id``:
    the real API narrows the candidate set to issues *linked* to the entry,
    which would exclude the unlinked issues written by pre-2026.11 versions
    of this integration — exactly the stale issues this refresh clears after
    an upgrade restart.
    """
    with ir.async_refresh_issues(
        hass,
        DOMAIN,
        issue_id_pattern=issue_id_pattern,
    ):
        yield


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


def async_create_unsupported_temperature_unit_issue(hass, entry) -> None:
    """Create a repair issue when Home Assistant uses Fahrenheit.

    The integration is blocked in that case (setup raises
    ``ConfigEntryError``), so the issue explains why no entities exist and
    what the user has to change.
    """
    issue_id = unsupported_temperature_unit_issue_id(entry)
    _create_issue(
        hass,
        entry,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.ERROR,
        translation_key=ISSUE_UNSUPPORTED_TEMPERATURE_UNIT,
        translation_placeholders={
            "entry_id": entry.entry_id,
            "entry_name": getattr(entry, "title", None) or entry.entry_id,
            "temperature_unit": str(hass.config.units.temperature_unit),
        },
    )
    _LOGGER.error(
        "Created unsupported temperature unit issue %s: %s",
        issue_id,
        hass.config.units.temperature_unit,
    )


def async_delete_unsupported_temperature_unit_issue(hass, entry) -> None:
    """Delete the unsupported-unit repair issue after a metric setup."""
    ir.async_delete_issue(hass, DOMAIN, unsupported_temperature_unit_issue_id(entry))


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
