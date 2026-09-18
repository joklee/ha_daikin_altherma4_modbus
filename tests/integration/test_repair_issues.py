"""Tests for repair issue helpers (Silver repair-issues coverage)."""

from types import SimpleNamespace

from homeassistant.helpers.issue_registry import async_get as async_get_issue_registry

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.integration.repair import (
    ISSUE_CONNECTION_LOST,
    ISSUE_DEVICE_ABNORMALITY,
    async_create_abnormality_issue,
    async_create_connection_issue,
    async_delete_abnormality_issue,
    async_delete_connection_issue,
)


def _entry():
    return SimpleNamespace(entry_id="test_entry", title="Test Pump")


async def test_connection_issue_lifecycle(hass, enable_custom_integrations):
    """Create and delete round-trips through the real issue registry."""
    entry = _entry()
    async_create_connection_issue(hass, entry, "Polling failed: boom")

    registry = async_get_issue_registry(hass)
    issue_id = f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}"
    assert (DOMAIN, issue_id) in registry.issues
    issue = registry.issues[(DOMAIN, issue_id)]
    assert issue.is_fixable is True
    assert "boom" in issue.translation_placeholders["error_message"]

    async_delete_connection_issue(hass, entry)
    assert (DOMAIN, issue_id) not in registry.issues


async def test_abnormality_issue_lifecycle(hass, enable_custom_integrations):
    """Abnormality issues are informational (not fixable) with code details."""
    entry = _entry()
    async_create_abnormality_issue(hass, entry, "A5", 12)

    registry = async_get_issue_registry(hass)
    issue_id = f"{ISSUE_DEVICE_ABNORMALITY}_{entry.entry_id}"
    assert (DOMAIN, issue_id) in registry.issues
    issue = registry.issues[(DOMAIN, issue_id)]
    assert issue.is_fixable is False
    assert issue.translation_placeholders["abnormality_code"] == "A5"
    assert issue.translation_placeholders["abnormality_sub_code"] == "12"

    async_delete_abnormality_issue(hass, entry)
    assert (DOMAIN, issue_id) not in registry.issues


async def test_connection_issue_without_title(hass, enable_custom_integrations):
    """Entries without a title fall back to the entry id."""
    entry = SimpleNamespace(entry_id="bare_entry")
    async_create_connection_issue(hass, entry, "down")

    registry = async_get_issue_registry(hass)
    issue = registry.issues[(DOMAIN, f"{ISSUE_CONNECTION_LOST}_bare_entry")]
    assert issue.translation_placeholders["entry_name"] == "bare_entry"

    async_delete_connection_issue(hass, entry)
