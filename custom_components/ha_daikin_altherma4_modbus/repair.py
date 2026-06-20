"""Repair issue management for Daikin Altherma 4 Modbus integration."""

import logging

from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Issue IDs
ISSUE_CONNECTION_LOST = "connection_lost"
ISSUE_DEVICE_ABNORMALITY = "device_abnormality"


def async_create_connection_issue(hass, entry, error_message: str) -> None:
    """Create a repair issue for connection loss.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        error_message: Description of the connection error
    """
    issue_id = f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}"
    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        is_persistent=False,
        severity=IssueSeverity.ERROR,
        translation_key=ISSUE_CONNECTION_LOST,
        translation_placeholders={
            "entry_id": entry.entry_id,
            "entry_name": entry.title,
            "error_message": error_message,
        },
    )
    _LOGGER.warning(
        "Created connection issue %s: %s", issue_id, error_message
    )


def async_delete_connection_issue(hass, entry) -> None:
    """Delete the connection repair issue for an entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    issue_id = f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}"
    async_delete_issue(hass, DOMAIN, issue_id)


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
    issue_id = f"{ISSUE_DEVICE_ABNORMALITY}_{entry.entry_id}"
    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.WARNING,
        translation_key=ISSUE_DEVICE_ABNORMALITY,
        translation_placeholders={
            "entry_id": entry.entry_id,
            "entry_name": entry.title,
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
    issue_id = f"{ISSUE_DEVICE_ABNORMALITY}_{entry.entry_id}"
    async_delete_issue(hass, DOMAIN, issue_id)