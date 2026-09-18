"""Edge-case tests for the configurable Modbus unit id.

Covers the reviewer checklist for the unit-id feature: validation
boundaries, reconfigure across units (incl. real reload), migration of
stored version-1 entries while the integration runs, and multi-entry
identity on a shared host/port (unique_id ``host:port:unit_id``).
"""

from unittest import mock

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import (
    CONF_UNIT_ID,
    DOMAIN,
)

HOST = "192.0.2.70"
PORT = 502


def _user_data(unit_id, **overrides):
    data = {
        CONF_HOST: HOST,
        CONF_PORT: PORT,
        CONF_UNIT_ID: unit_id,
        "scan_interval": 15,
        "slow_scan_interval": 300,
        "demo_mode": True,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
@pytest.mark.parametrize("unit_id", [0, 248, 255])
async def test_user_flow_rejects_out_of_range_unit_id(
    hass, enable_custom_integrations, unit_id
):
    """Unit ids outside 1..247 are rejected with invalid_unit_id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=_user_data(unit_id),
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_UNIT_ID] == "invalid_unit_id"


@pytest.mark.asyncio
async def test_user_flow_accepts_boundary_unit_id(hass, enable_custom_integrations):
    """Unit id 247 (upper boundary) creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=_user_data(247),
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_UNIT_ID] == 247


@pytest.mark.asyncio
async def test_reconfigure_unit_1_to_2(hass, enable_custom_integrations):
    """Reconfigure moves an entry from unit 1 to unit 2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{HOST}:{PORT}:1",
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_UNIT_ID: 1},
        options={"scan_interval": 15, "demo_mode": True},
    )
    entry.add_to_hass(hass)

    with mock.patch.object(
        hass.config_entries, "async_schedule_reload", new=mock.MagicMock()
    ) as reload_mock:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_UNIT_ID: 2,
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": True,
            },
        )

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_UNIT_ID] == 2
    assert entry.unique_id == f"{HOST}:{PORT}:2"
    reload_mock.assert_called_once_with(entry.entry_id)


@pytest.mark.asyncio
async def test_reload_after_reconfigure_applies_new_unit(
    hass, enable_custom_integrations
):
    """A real reload after reconfigure brings up the new unit id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{HOST}:{PORT}:1",
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_UNIT_ID: 1},
        options={
            "scan_interval": 5,
            "slow_scan_interval": 30,
            "demo_mode": True,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()
    assert entry.runtime_data.manager.unit_id == 1

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_UNIT_ID: 2,
            "scan_interval": 5,
            "slow_scan_interval": 30,
            "demo_mode": True,
        },
    )

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.data[CONF_UNIT_ID] == 2
    assert entry.unique_id == f"{HOST}:{PORT}:2"
    assert entry.runtime_data.manager.unit_id == 2


@pytest.mark.asyncio
async def test_migration_while_running(hass, enable_custom_integrations):
    """A stored v1 entry migrates (data + unique_id) and loads."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title=f"Daikin Altherma 4 ({HOST})",
        unique_id=f"{HOST}:{PORT}",
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        options={
            "scan_interval": 5,
            "slow_scan_interval": 30,
            "demo_mode": True,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_UNIT_ID] == 1
    assert entry.unique_id == f"{HOST}:{PORT}:1"
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.manager.unit_id == 1


@pytest.mark.asyncio
async def test_two_entries_same_endpoint_different_units(
    hass, enable_custom_integrations
):
    """Two units behind one host/port coexist as separate entries."""
    first = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=_user_data(1),
    )
    assert first["type"] == "create_entry"

    second = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=_user_data(2),
    )
    assert second["type"] == "create_entry"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert {entry.unique_id for entry in entries} == {
        f"{HOST}:{PORT}:1",
        f"{HOST}:{PORT}:2",
    }


@pytest.mark.asyncio
async def test_same_triple_is_rejected(hass, enable_custom_integrations):
    """The same host/port/unit triple cannot be configured twice.

    Critical with the shared connection: two entries for one unit would
    fight over the same device state.
    """
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{HOST}:{PORT}:2",
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_UNIT_ID: 2},
        options={"scan_interval": 15, "demo_mode": True},
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=_user_data(2),
    )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_reconfigure_onto_used_triple_aborts(hass, enable_custom_integrations):
    """Reconfigure onto another entry's triple aborts as already_configured."""
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{HOST}:{PORT}:1",
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_UNIT_ID: 1},
        options={"scan_interval": 15},
    )
    entry_b = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{HOST}:{PORT}:2",
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_UNIT_ID: 2},
        options={"scan_interval": 15},
    )
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    with mock.patch.object(
        hass.config_entries, "async_schedule_reload", new=mock.MagicMock()
    ) as reload_mock:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry_a.entry_id,
            },
            data={
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_UNIT_ID: 2,  # already used by entry_b
                "scan_interval": 15,
                "slow_scan_interval": 300,
                "demo_mode": True,
            },
        )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
    assert entry_a.data[CONF_UNIT_ID] == 1
    assert entry_a.unique_id == f"{HOST}:{PORT}:1"
    reload_mock.assert_not_called()
