"""Config entry migration tests (schema version 1 -> 2).

Schema version 2 introduced ``unit_id`` in the config entry ``data``.
Stored version-1 entries must be migrated automatically at boot without
user interaction: ``unit_id`` defaults to 1 (direct TCP link) and all
other fields stay untouched.
"""

from unittest import mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_daikin_altherma4_modbus.core.const import (
    CONF_UNIT_ID,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from custom_components.ha_daikin_altherma4_modbus.integration import (
    config_flow as config_flow_module,
)

HOST = "192.0.2.60"
PORT = 502


@pytest.mark.real_ha
async def test_version_1_entry_is_migrated_to_version_2_with_default_unit_id(
    hass, enable_custom_integrations
):
    """A stored version-1 entry gains unit_id=1 and version 2 during setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title=f"Daikin Altherma 4 ({HOST})",
        unique_id=f"{HOST}:{PORT}",
        data={CONF_HOST: HOST, CONF_PORT: PORT},
    )
    entry.add_to_hass(hass)

    with mock.patch.object(
        config_flow_module,
        "_test_connection",
        new=mock.AsyncMock(return_value=(False, "cannot_connect")),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Migration runs before the setup attempt, therefore the entry has been
    # migrated even though the (mocked) connection setup fails afterwards.
    assert entry.version == 2
    assert entry.data[CONF_UNIT_ID] == DEFAULT_UNIT_ID
    # Existing data must not be touched by the migration.
    assert entry.data[CONF_HOST] == HOST
    assert entry.data[CONF_PORT] == PORT
    # The old-style unique_id gains the default unit id.
    assert entry.unique_id == f"{HOST}:{PORT}:{DEFAULT_UNIT_ID}"
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.real_ha
async def test_version_2_entry_passes_migration_unchanged(
    hass, enable_custom_integrations
):
    """A version-2 entry (incl. custom unit_id) is not modified by migration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title=f"Daikin Altherma 4 ({HOST})",
        unique_id=f"{HOST}:{PORT}:3",
        data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_UNIT_ID: 3},
    )
    entry.add_to_hass(hass)

    with mock.patch.object(
        config_flow_module,
        "_test_connection",
        new=mock.AsyncMock(return_value=(False, "cannot_connect")),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_UNIT_ID] == 3
    assert entry.unique_id == f"{HOST}:{PORT}:3"
    assert entry.state is ConfigEntryState.SETUP_RETRY
