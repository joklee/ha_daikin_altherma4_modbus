"""Tests for repair issue helpers (Silver repair-issues coverage)."""

import re
from contextlib import contextmanager

import pytest
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


def test_refresh_issue_set_uses_native_api(hass, monkeypatch):
    """The refresh helper delegates to HA's native refresh API, pattern-only.

    No ``config_entry_id`` goes along: the native API narrows the scope to
    linked issues and would thus miss the unlinked issues left behind by
    pre-2026.11 versions during an upgrade restart.
    """
    entry = _entry(hass)
    calls = []

    @contextmanager
    def fake_refresh_issues(hass_, domain, **kwargs):
        calls.append((domain, kwargs))
        yield

    monkeypatch.setattr(
        repair.ir, "async_refresh_issues", fake_refresh_issues, raising=False
    )

    with repair.async_refresh_issue_set(hass, entry, "pattern"):
        pass

    assert calls == [(DOMAIN, {"issue_id_pattern": "pattern"})]


def test_create_issue_links_entry(hass, monkeypatch):
    """Issues are created linked to the config entry."""
    entry = _entry(hass)
    captured = {}

    def fake_create_issue(hass_, domain, issue_id, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(repair.ir, "async_create_issue", fake_create_issue)

    repair.async_create_connection_issue(hass, entry, "boom")

    assert captured["config_entry_id"] == entry.entry_id


def _create_marker_issue(hass, entry, issue_id, severity=ir.IssueSeverity.ERROR):
    """Create a raw issue in the registry, as a previous run would have left it."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=severity,
        translation_key="device_abnormality",
        translation_placeholders={},
    )


def test_refresh_keeps_recreated_issue(hass):
    """An existing issue recreated inside the refresh survives."""
    entry = _entry(hass)
    issue_id = f"device_abnormality_{entry.entry_id}"
    _create_marker_issue(hass, entry, issue_id)

    with repair.async_refresh_issue_set(hass, entry, abnormality_issue_pattern(entry)):
        _create_marker_issue(hass, entry, issue_id)

    assert (DOMAIN, issue_id) in async_get_issue_registry(hass).issues


def test_refresh_deletes_untouched_issue(hass):
    """An existing issue not recreated inside the refresh is deleted."""
    entry = _entry(hass)
    issue_id = f"device_abnormality_{entry.entry_id}"
    _create_marker_issue(hass, entry, issue_id)

    with repair.async_refresh_issue_set(hass, entry, abnormality_issue_pattern(entry)):
        pass

    assert (DOMAIN, issue_id) not in async_get_issue_registry(hass).issues


def test_refresh_keeps_newly_created_issue(hass):
    """An issue first created inside the refresh is not affected."""
    entry = _entry(hass)
    issue_id = f"device_abnormality_{entry.entry_id}"

    with repair.async_refresh_issue_set(hass, entry, abnormality_issue_pattern(entry)):
        _create_marker_issue(hass, entry, issue_id)

    assert (DOMAIN, issue_id) in async_get_issue_registry(hass).issues


@pytest.mark.skipif(not hasattr(ir, "async_ignore_issue"), reason="HA < 2026.10")
def test_refresh_keeps_ignored_recreated_issue(hass):
    """A recreated ignored issue survives and keeps its ignore flag."""
    entry = _entry(hass)
    issue_id = f"device_abnormality_{entry.entry_id}"
    _create_marker_issue(hass, entry, issue_id)
    ir.async_ignore_issue(hass, DOMAIN, issue_id, ignore=True)

    with repair.async_refresh_issue_set(hass, entry, abnormality_issue_pattern(entry)):
        _create_marker_issue(hass, entry, issue_id)

    issue = async_get_issue_registry(hass).issues[(DOMAIN, issue_id)]
    assert issue.dismissed_version is not None


def test_refresh_cancels_on_error(hass):
    """An exception inside the refresh cancels it and deletes nothing."""
    entry = _entry(hass)
    issue_id = f"device_abnormality_{entry.entry_id}"
    _create_marker_issue(hass, entry, issue_id)

    with (
        pytest.raises(RuntimeError),
        repair.async_refresh_issue_set(hass, entry, abnormality_issue_pattern(entry)),
    ):
        raise RuntimeError("boom")

    assert (DOMAIN, issue_id) in async_get_issue_registry(hass).issues
