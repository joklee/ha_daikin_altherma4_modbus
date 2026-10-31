"""Tests for repair issue helpers (Silver repair-issues coverage)."""

import re
from contextlib import contextmanager

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import async_get as async_get_issue_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import DOMAIN
from custom_components.ha_daikin_altherma4_modbus.integration import repair
from custom_components.ha_daikin_altherma4_modbus.integration.repair import (
    ISSUE_CONNECTION_LOST,
    ISSUE_DEVICE_ABNORMALITY,
    abnormality_issue_id,
    abnormality_issue_pattern,
    async_create_abnormality_issue,
    async_create_connection_issue,
    async_delete_abnormality_issue,
    async_delete_connection_issue,
    async_refresh_issue_set,
    connection_issue_id,
)


def _entry(hass, title="Test Pump"):
    entry = MockConfigEntry(domain=DOMAIN, title=title)
    entry.add_to_hass(hass)
    return entry


async def test_connection_issue_lifecycle(hass, enable_custom_integrations):
    """Create and delete round-trips through the real issue registry."""
    entry = _entry(hass)
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
    entry = _entry(hass)
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
    entry = _entry(hass, title="")
    async_create_connection_issue(hass, entry, "down")

    registry = async_get_issue_registry(hass)
    issue = registry.issues[(DOMAIN, f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}")]
    assert issue.translation_placeholders["entry_name"] == entry.entry_id

    async_delete_connection_issue(hass, entry)


def test_issue_ids_and_refresh_pattern(hass):
    """Issue ids include the entry id and the pattern matches only that issue."""
    entry = _entry(hass)
    assert connection_issue_id(entry) == f"{ISSUE_CONNECTION_LOST}_{entry.entry_id}"
    assert abnormality_issue_id(entry) == f"{ISSUE_DEVICE_ABNORMALITY}_{entry.entry_id}"
    pattern = abnormality_issue_pattern(entry)
    assert re.fullmatch(pattern, abnormality_issue_id(entry))
    assert re.fullmatch(pattern, f"{ISSUE_DEVICE_ABNORMALITY}_other") is None


def test_refresh_issue_set_uses_native_api_when_available(hass):
    """The refresh helper reports whether the HA 2026.11+ API is active."""
    entry = _entry(hass)
    with async_refresh_issue_set(hass, entry, "connection_lost_") as refreshed:
        assert refreshed is hasattr(ir, "async_refresh_issues")


def test_create_issue_links_entry_when_supported(hass, monkeypatch):
    """HA 2026.11+ creates issues linked to the config entry."""
    entry = _entry(hass)
    captured = {}

    def fake_create_issue(hass_, domain, issue_id, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(repair, "_SUPPORTS_CONFIG_ENTRY_ID", True)
    monkeypatch.setattr(repair.ir, "async_create_issue", fake_create_issue)

    repair.async_create_connection_issue(hass, entry, "boom")

    assert captured["config_entry_id"] == entry.entry_id


def test_refresh_issue_set_uses_native_api_when_supported(hass, monkeypatch):
    """HA 2026.11+ refreshes issues without falling back to explicit deletes."""
    entry = _entry(hass)
    calls = []

    @contextmanager
    def fake_refresh_issues(hass_, domain, **kwargs):
        calls.append((domain, kwargs))
        yield

    monkeypatch.setattr(repair, "_SUPPORTS_CONFIG_ENTRY_ID", True)
    monkeypatch.setattr(
        repair.ir, "async_refresh_issues", fake_refresh_issues, raising=False
    )

    with repair.async_refresh_issue_set(hass, entry, "pattern") as refreshed:
        assert refreshed is True

    assert calls == [
        (
            DOMAIN,
            {"issue_id_pattern": "pattern", "config_entry_id": entry.entry_id},
        )
    ]
