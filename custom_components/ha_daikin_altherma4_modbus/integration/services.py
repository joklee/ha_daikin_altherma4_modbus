"""Services for Daikin Altherma 4 Modbus integration."""

import asyncio
import logging
import time
from datetime import timedelta

try:
    import voluptuous as vol
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
    from homeassistant.helpers import config_validation as cv
    from homeassistant.helpers.service import async_register_admin_service
    from homeassistant.helpers.storage import Store

    HAS_HA = True
except ImportError:
    # Fallback for testing when homeassistant is not available
    HAS_HA = False

from ..common.helpers import (
    get_register_scale,
    get_register_value,
    is_unavailable_value,
    scaled_value_to_register,
)
from ..core.const import (
    DOMAIN,
    HVAC_COOL,
    HVAC_HEAT,
    HVAC_OFF,
    REGISTER_DHW_HVAC_MODE,
    REGISTER_OPERATION_MODE,
    SERVICE_REFRESH_CONNECTION,
    SERVICE_SET_ADDITIONAL_ZONE_SETPOINT,
    SERVICE_SET_ADDITIONAL_ZONE_STATE,
    SERVICE_SET_COOLING_OFFSET,
    SERVICE_SET_DHW_BOOSTER_MODE,
    SERVICE_SET_DHW_SINGLE_HEATUP,
    SERVICE_SET_DHW_STATE,
    SERVICE_SET_HEATING_OFFSET,
    SERVICE_SET_MAIN_ZONE_STATE,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_POWER_LIMIT,
    SERVICE_SET_QUIET_MODE,
    SERVICE_SET_ROOM_COOLING_SETPOINT,
    SERVICE_SET_ROOM_HEATING_SETPOINT,
    SERVICE_SET_SMART_GRID_MODE,
    SERVICE_START_DHW_SINGLE_HEATUP,
)
from ..core.register_constants import HOLDING_REGISTERS
from .repair import (
    async_create_dhw_heatup_restore_issue,
    async_delete_dhw_heatup_restore_issue,
)

_LOGGER = logging.getLogger(__name__)

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_OPERATION_MODE = "operation_mode"
ATTR_STATE = "state"
ATTR_SMART_GRID_MODE = "smart_grid_mode"
ATTR_QUIET_MODE = "quiet_mode"
ATTR_BOOSTER_MODE = "booster_mode"
ATTR_SINGLE_HEATUP = "single_heatup"
ATTR_SETPOINT = "setpoint"
ATTR_POWER_LIMIT = "power_limit"
ATTR_OFFSET = "offset"
ATTR_TARGET_TEMPERATURE = "target_temperature"
ATTR_TIMEOUT = "timeout"
ATTR_HYSTERESIS = "hysteresis"

# DHW single heat-up run (issue #21): status poll interval and finish event.
_DHW_RUN_STATUS_POLL_INTERVAL = 30.0
EVENT_DHW_SINGLE_HEATUP_FINISHED = (
    "ha_daikin_altherma4_modbus_dhw_single_heatup_finished"
)

# Maximum accepted age of the DHW temperature reading used to decide whether
# the heat-up target was reached. Older data is ignored until a fresh poll
# arrives, so a stale cache can never end a run prematurely.
_DHW_MAX_DATA_AGE = 300.0

# Persistent recovery state version and storage key prefix.
_DHW_STATE_VERSION = 1
_DHW_STATE_KEY_PREFIX = f"{DOMAIN}.dhw_single_heatup"

# Running single heat-up runs by config entry id. Cancelled on unload so no
# write ever targets a torn-down device.
_SINGLE_HEATUP_TASKS: dict = {}

# Per-entry locks serializing start/cancel of single heat-up runs so the
# "already running" check and task registration are atomic.
_SINGLE_HEATUP_LOCKS: dict = {}


def _single_heatup_lock(config_entry_id: str) -> asyncio.Lock:
    """Return the per-entry lock for single heat-up start/cancel."""
    lock = _SINGLE_HEATUP_LOCKS.get(config_entry_id)
    if lock is None:
        lock = asyncio.Lock()
        _SINGLE_HEATUP_LOCKS[config_entry_id] = lock
    return lock


# Operation mode mapping for service calls (lowercase keys for service API)
OPERATION_MODE_MAP = {
    "off": HVAC_OFF,
    "heat": HVAC_HEAT,
    "cool": HVAC_COOL,
}


# Smart Grid mode mapping for service calls (lowercase keys for service API)
def get_smart_grid_mode_map():
    """Get Smart Grid mode mapping from register constants."""
    # Find the Smart Grid register in HOLDING_REGISTERS
    for register in HOLDING_REGISTERS:
        if register.register_name == "holding_56":
            return {v.lower(): k for k, v in register.enum_map.items()}
    return {}


# Quiet mode mapping for service calls (lowercase keys for service API)
def get_quiet_mode_map():
    """Get Quiet mode mapping from register constants."""
    # Find the Quiet mode register in HOLDING_REGISTERS
    for register in HOLDING_REGISTERS:
        if register.register_name == "holding_9":
            return {v.lower(): k for k, v in register.enum_map.items()}
    return {}


# Service schemas (only defined when HA is available)
if HAS_HA:
    SERVICE_SET_OPERATION_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_OPERATION_MODE): vol.In(["off", "heat", "cool"]),
        }
    )

    SERVICE_SET_DHW_STATE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_STATE): cv.boolean,
        }
    )

    SERVICE_SET_MAIN_ZONE_STATE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_STATE): cv.boolean,
        }
    )

    SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_STATE): cv.boolean,
        }
    )

    # Get Smart Grid mode options from register constants
    smart_grid_options = list(get_smart_grid_mode_map().keys())
    SERVICE_SET_SMART_GRID_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SMART_GRID_MODE): vol.In(smart_grid_options),
        }
    )

    # Get Quiet mode options from register constants
    quiet_mode_options = list(get_quiet_mode_map().keys())
    SERVICE_SET_QUIET_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_QUIET_MODE): vol.In(quiet_mode_options),
        }
    )

    SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_BOOSTER_MODE): cv.boolean,
        }
    )

    SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SINGLE_HEATUP): cv.boolean,
            vol.Optional(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=30, max=85)
            ),
        }
    )

    SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_TARGET_TEMPERATURE): vol.All(
                vol.Coerce(float), vol.Range(min=30, max=85)
            ),
            vol.Optional(ATTR_TIMEOUT, default=timedelta(hours=2)): vol.All(
                cv.time_period,
                vol.Range(min=timedelta(seconds=60), max=timedelta(hours=6)),
            ),
            vol.Optional(ATTR_HYSTERESIS, default=0.5): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=5)
            ),
        }
    )

    SERVICE_SET_POWER_LIMIT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_POWER_LIMIT): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=20)
            ),
        }
    )

    SERVICE_SET_HEATING_OFFSET_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_OFFSET): vol.All(
                vol.Coerce(float), vol.Range(min=-10, max=10)
            ),
        }
    )

    SERVICE_SET_COOLING_OFFSET_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_OFFSET): vol.All(
                vol.Coerce(float), vol.Range(min=-10, max=10)
            ),
        }
    )

    SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=12, max=30)
            ),
        }
    )

    SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=12, max=35)
            ),
        }
    )

    SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_SETPOINT): vol.All(
                vol.Coerce(float), vol.Range(min=3, max=85)
            ),
        }
    )

    SERVICE_REFRESH_CONNECTION_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        }
    )
else:
    # Placeholders for testing - create dummy schemas that accept anything
    def _make_dummy_schema(fields):
        class DummySchema:
            def __call__(self, data):
                return data

        return DummySchema()

    SERVICE_SET_OPERATION_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_DHW_STATE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_MAIN_ZONE_STATE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_SMART_GRID_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_QUIET_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA = _make_dummy_schema(None)
    SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_POWER_LIMIT_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_HEATING_OFFSET_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_COOLING_OFFSET_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA = _make_dummy_schema(None)
    SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA = _make_dummy_schema(None)
    SERVICE_REFRESH_CONNECTION_SCHEMA = _make_dummy_schema(None)


def get_operation_mode_map():
    """Return the operation mode mapping."""
    return OPERATION_MODE_MAP.copy()


if HAS_HA:

    async def _guarded_write(register_name, write_call):
        """Execute a Modbus write, surfacing failures as HomeAssistantError.

        Silver ``action-exceptions``: service calls must raise HA exceptions
        so the frontend shows a translatable error instead of an unexpected
        traceback from the transport layer.
        """
        try:
            return await write_call()
        except (HomeAssistantError, ServiceValidationError):
            raise
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={
                    "operation_name": "write",
                    "register_type": "register",
                    "register_name": register_name,
                    "error": str(err),
                },
            ) from err

    def _get_entry_and_validate(hass, config_entry_id):
        """Get config entry and validate it's loaded."""
        entry = hass.config_entries.async_get_entry(config_entry_id)
        if entry is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_found",
                translation_placeholders={"config_entry_id": config_entry_id},
            )
        if entry.state != ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
                translation_placeholders={"config_entry_id": config_entry_id},
            )
        return entry

    # ------------------------------------------------------------------
    # DHW single heat-up helpers: freshness, direct reads, persistence
    # ------------------------------------------------------------------

    def _dhw_state_store(hass, config_entry_id: str) -> Store:
        """Return the persistent store for a single heat-up run."""
        return Store(
            hass,
            _DHW_STATE_VERSION,
            f"{_DHW_STATE_KEY_PREFIX}.{config_entry_id}",
        )

    async def _async_load_dhw_state(hass, config_entry_id: str) -> dict | None:
        """Load persisted single heat-up recovery state, if any."""
        try:
            data = await _dhw_state_store(hass, config_entry_id).async_load()
        except Exception as err:
            _LOGGER.warning(
                "Could not load DHW single heat-up recovery state for entry %s: %s",
                config_entry_id,
                err,
            )
            return None
        return data if isinstance(data, dict) else None

    async def _async_save_dhw_state(hass, config_entry_id: str, state: dict) -> None:
        """Persist single heat-up recovery state before changing the device."""
        await _dhw_state_store(hass, config_entry_id).async_save(state)

    async def _async_clear_dhw_state(hass, config_entry_id: str) -> None:
        """Remove persisted single heat-up recovery state."""
        try:
            await _dhw_state_store(hass, config_entry_id).async_remove()
        except Exception as err:
            _LOGGER.warning(
                "Could not clear DHW single heat-up recovery state for entry %s: %s",
                config_entry_id,
                err,
            )

    def _dhw_temperature_age(manager) -> float | None:
        """Return the age of the last successful normal poll in seconds."""
        normal = getattr(manager, "normal_coordinator", None)
        last = getattr(normal, "last_successful_poll", None) if normal else None
        if last is None:
            return None
        return max(0.0, time.monotonic() - last)

    def _dhw_temperature_is_fresh(manager) -> bool:
        """Whether cached DHW temperature data is recent enough to trust."""
        normal = getattr(manager, "normal_coordinator", None)
        if normal is None or getattr(normal, "last_update_success", False) is not True:
            return False
        age = _dhw_temperature_age(manager)
        return age is not None and age <= _DHW_MAX_DATA_AGE

    async def _resolve_dhw_enabled(manager, writer) -> bool | None:
        """Return the current DHW state, preferring a direct device read."""
        reader = getattr(writer, "read_coil_register", None)
        if callable(reader):
            try:
                raw = await reader(REGISTER_DHW_HVAC_MODE)
            except Exception as err:
                _LOGGER.debug(
                    "Direct DHW state read failed; falling back to cached "
                    "coordinator data: %s",
                    err,
                )
            else:
                if raw is not None:
                    return bool(raw)
        return _dhw_enabled(manager)

    async def _resolve_dhw_heatup_setpoint(manager, writer) -> int | None:
        """Return the raw holding_16 value, preferring a direct device read."""
        reader = getattr(writer, "read_holding_register", None)
        if callable(reader):
            try:
                raw = await reader("holding_16")
            except Exception as err:
                _LOGGER.debug(
                    "Direct DHW setpoint read failed; falling back to cached "
                    "coordinator data: %s",
                    err,
                )
            else:
                if raw is not None:
                    try:
                        return int(raw)
                    except (TypeError, ValueError):
                        pass
        return _dhw_heatup_setpoint(manager)

    def _dhw_heatup_request_active(manager) -> int | None:
        """Return the cached holding_15 value, or None when unknown."""
        try:
            data = manager.get_all_data()
        except Exception:  # pragma: no cover - defensive
            return None
        raw = get_register_value(data.get("holding_15"))
        if raw is None or is_unavailable_value(raw):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    async def _restore_dhw_heatup_state(
        hass,
        entry,
        writer,
        *,
        previous_setpoint: int | None,
        restore_setpoint: bool,
        restore_dhw_off: bool,
        dhw_coil_name: str = REGISTER_DHW_HVAC_MODE,
    ) -> list[str]:
        """Restore the pre-run device state and report failed steps.

        Always clears the heat-up request. Optionally restores the previous
        setpoint and the DHW off state. A repair issue is created when any
        step fails and deleted after a complete restore.
        """
        config_entry_id = entry.entry_id
        failures: list[str] = []

        try:
            await writer.write_holding_register("holding_15", 0)
        except Exception as err:
            failures.append(f"clear heat-up request: {err}")
            _LOGGER.error(
                "Could not clear DHW heat-up request for entry %s: %s",
                config_entry_id,
                err,
            )

        if restore_setpoint:
            if previous_setpoint is None:
                failures.append("previous setpoint unknown")
            else:
                try:
                    await writer.write_holding_register("holding_16", previous_setpoint)
                    _LOGGER.debug(
                        "Restored DHW single heat-up setpoint to %s for entry %s",
                        previous_setpoint,
                        config_entry_id,
                    )
                except Exception as err:
                    failures.append(f"restore setpoint: {err}")
                    _LOGGER.error(
                        "Could not restore DHW single heat-up setpoint for "
                        "entry %s: %s",
                        config_entry_id,
                        err,
                    )

        if restore_dhw_off:
            try:
                await writer.write_coil_register(dhw_coil_name, False)
                _LOGGER.debug("Restored DHW off state for entry %s", config_entry_id)
            except Exception as err:
                failures.append(f"restore DHW off: {err}")
                _LOGGER.error(
                    "Could not restore DHW off state for entry %s: %s",
                    config_entry_id,
                    err,
                )

        if failures:
            async_create_dhw_heatup_restore_issue(hass, entry, "; ".join(failures))
        else:
            async_delete_dhw_heatup_restore_issue(hass, entry)
        return failures

    async def async_set_operation_mode(call) -> None:
        """Set the heat pump operation mode."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        operation_mode = call.data[ATTR_OPERATION_MODE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        mode_value = OPERATION_MODE_MAP.get(operation_mode)
        if mode_value is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_operation_mode",
                translation_placeholders={"operation_mode": operation_mode},
            )

        await _guarded_write(
            REGISTER_OPERATION_MODE,
            lambda: writer.write_holding_register(REGISTER_OPERATION_MODE, mode_value),
        )
        _LOGGER.debug(
            "Set operation mode to %s (value: %s) for entry %s",
            operation_mode,
            mode_value,
            config_entry_id,
        )

    async def async_set_dhw_state(call) -> None:
        """Enable or disable Domestic Hot Water."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        state = call.data[ATTR_STATE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        await _guarded_write(
            REGISTER_DHW_HVAC_MODE,
            lambda: writer.write_coil_register(REGISTER_DHW_HVAC_MODE, state),
        )
        _LOGGER.debug(
            "Set DHW state to %s for entry %s",
            state,
            config_entry_id,
        )

    async def async_set_main_zone_state(call) -> None:
        """Enable or disable the main zone."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        state = call.data[ATTR_STATE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Main zone is coil_2
        await _guarded_write(
            "coil_2", lambda: writer.write_coil_register("coil_2", state)
        )
        _LOGGER.debug(
            "Set main zone state to %s for entry %s",
            state,
            config_entry_id,
        )

    async def async_set_additional_zone_state(call) -> None:
        """Enable or disable the additional zone."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        state = call.data[ATTR_STATE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Additional zone is coil_3
        await _guarded_write(
            "coil_3", lambda: writer.write_coil_register("coil_3", state)
        )
        _LOGGER.debug(
            "Set additional zone state to %s for entry %s",
            state,
            config_entry_id,
        )

    async def async_set_smart_grid_mode(call) -> None:
        """Set the Smart Grid operation mode."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        smart_grid_mode = call.data.get(ATTR_SMART_GRID_MODE)

        if smart_grid_mode is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_smart_grid_mode",
                translation_placeholders={"smart_grid_mode": "None"},
            )

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        smart_grid_mode_map = get_smart_grid_mode_map()
        mode_value = smart_grid_mode_map.get(smart_grid_mode)
        if mode_value is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_smart_grid_mode",
                translation_placeholders={"smart_grid_mode": smart_grid_mode},
            )

        await _guarded_write(
            "holding_56",
            lambda: writer.write_holding_register("holding_56", mode_value),
        )
        _LOGGER.debug(
            "Set Smart Grid mode to %s (value: %s) for entry %s",
            smart_grid_mode,
            mode_value,
            config_entry_id,
        )

    async def async_set_quiet_mode(call) -> None:
        """Set the Quiet mode operation."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        quiet_mode = call.data[ATTR_QUIET_MODE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        quiet_mode_map = get_quiet_mode_map()
        mode_value = quiet_mode_map.get(quiet_mode)
        if mode_value is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_quiet_mode",
                translation_placeholders={"quiet_mode": quiet_mode},
            )

        await _guarded_write(
            "holding_9",
            lambda: writer.write_holding_register("holding_9", mode_value),
        )
        _LOGGER.debug(
            "Set Quiet mode to %s (value: %s) for entry %s",
            quiet_mode,
            mode_value,
            config_entry_id,
        )

    async def async_set_dhw_booster_mode(call) -> None:
        """Set the DHW booster mode."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        booster_mode = call.data[ATTR_BOOSTER_MODE]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        await _guarded_write(
            "holding_13",
            lambda: writer.write_holding_register(
                "holding_13", 1 if booster_mode else 0
            ),
        )
        _LOGGER.debug(
            "Set DHW booster mode to %s for entry %s",
            booster_mode,
            config_entry_id,
        )

    async def async_set_dhw_single_heatup(call) -> None:
        """Set the DHW single heat-up mode and optional setpoint."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        single_heatup = call.data[ATTR_SINGLE_HEATUP]
        setpoint = call.data.get(ATTR_SETPOINT)

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager
        writer = runtime_data.coordinator.data_manager

        setpoint_written = False
        previous_setpoint = None
        if setpoint is not None:
            # A setpoint change is only safe when the previous value is known
            # and can be restored if the activation fails.
            previous_setpoint = await _resolve_dhw_heatup_setpoint(manager, writer)
            if previous_setpoint is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="single_heatup_setpoint_unknown",
                    translation_placeholders={"config_entry_id": config_entry_id},
                )
            # Convert setpoint to register value (scale by 0.01)
            register_value = scaled_value_to_register(setpoint, 0.01)
            await _guarded_write(
                "holding_16",
                lambda: writer.write_holding_register("holding_16", register_value),
            )
            setpoint_written = True

        try:
            await _guarded_write(
                "holding_15",
                lambda: writer.write_holding_register(
                    "holding_15", 1 if single_heatup else 0
                ),
            )
        except (Exception, asyncio.CancelledError):
            failures = await _restore_dhw_heatup_state(
                hass,
                entry,
                writer,
                previous_setpoint=previous_setpoint,
                restore_setpoint=setpoint_written,
                restore_dhw_off=False,
            )
            if not failures:
                await _async_clear_dhw_state(hass, config_entry_id)
            raise

        if setpoint is not None:
            _LOGGER.debug(
                "Set DHW single heat-up to %s with setpoint %s°C for entry %s",
                single_heatup,
                setpoint,
                config_entry_id,
            )
        else:
            _LOGGER.debug(
                "Set DHW single heat-up to %s for entry %s",
                single_heatup,
                config_entry_id,
            )

    async def async_set_power_limit(call) -> None:
        """Set the imposed power limit."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        power_limit = call.data[ATTR_POWER_LIMIT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Convert power limit to register value (scale by 0.001)
        register_value = scaled_value_to_register(power_limit, 0.001)
        await _guarded_write(
            "holding_58",
            lambda: writer.write_holding_register("holding_58", register_value),
        )
        _LOGGER.debug(
            "Set power limit to %s kW (value: %s) for entry %s",
            power_limit,
            register_value,
            config_entry_id,
        )

    async def async_set_heating_offset(call) -> None:
        """Set the weather-dependent heating offset."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        offset = call.data[ATTR_OFFSET]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Convert offset to register value (scale by 0.01)
        register_value = scaled_value_to_register(offset, 0.01)
        await _guarded_write(
            "holding_54",
            lambda: writer.write_holding_register("holding_54", register_value),
        )
        _LOGGER.debug(
            "Set heating offset to %s °C (value: %s) for entry %s",
            offset,
            register_value,
            config_entry_id,
        )

    async def async_set_cooling_offset(call) -> None:
        """Set the weather-dependent cooling offset."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        offset = call.data[ATTR_OFFSET]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Convert offset to register value (scale by 0.01)
        register_value = scaled_value_to_register(offset, 0.01)
        await _guarded_write(
            "holding_55",
            lambda: writer.write_holding_register("holding_55", register_value),
        )
        _LOGGER.debug(
            "Set cooling offset to %s °C (value: %s) for entry %s",
            offset,
            register_value,
            config_entry_id,
        )

    async def async_set_room_heating_setpoint(call) -> None:
        """Set the room thermostat heating setpoint."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        setpoint = call.data[ATTR_SETPOINT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Convert setpoint to register value (scale by 0.01)
        register_value = scaled_value_to_register(setpoint, 0.01)
        await _guarded_write(
            "holding_6",
            lambda: writer.write_holding_register("holding_6", register_value),
        )
        _LOGGER.debug(
            "Set room heating setpoint to %s°C (value: %s) for entry %s",
            setpoint,
            register_value,
            config_entry_id,
        )

    async def async_set_room_cooling_setpoint(call) -> None:
        """Set the room thermostat cooling setpoint."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        setpoint = call.data[ATTR_SETPOINT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Convert setpoint to register value (scale by 0.01)
        register_value = scaled_value_to_register(setpoint, 0.01)
        await _guarded_write(
            "holding_7",
            lambda: writer.write_holding_register("holding_7", register_value),
        )
        _LOGGER.debug(
            "Set room cooling setpoint to %s°C (value: %s) for entry %s",
            setpoint,
            register_value,
            config_entry_id,
        )

    async def async_set_additional_zone_setpoint(call) -> None:
        """Set the additional zone setpoint."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        setpoint = call.data[ATTR_SETPOINT]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        writer = runtime_data.coordinator.data_manager

        # Convert setpoint to register value (scale by 0.01)
        register_value = scaled_value_to_register(setpoint, 0.01)
        await _guarded_write(
            "holding_63",
            lambda: writer.write_holding_register("holding_63", register_value),
        )
        _LOGGER.debug(
            "Set additional zone setpoint to %s°C (value: %s) for entry %s",
            setpoint,
            register_value,
            config_entry_id,
        )

    async def async_refresh_connection(call) -> None:
        """Refresh the Modbus connection for the specified entry."""
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager

        # Trigger connection refresh by reconnecting
        await _guarded_write("connection", manager.refresh_connection)
        _LOGGER.debug(
            "Refreshed connection for entry %s",
            config_entry_id,
        )

    def _dhw_temperature(manager) -> float | None:
        """Return the latest DHW temperature from coordinator data, if known."""
        try:
            data = manager.get_all_data()
        except Exception:  # pragma: no cover - defensive
            return None
        raw = get_register_value(data.get("input_43"))
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    def _dhw_enabled(manager) -> bool | None:
        """Return True/False for DHW (coil_1), or None when unknown."""
        try:
            data = manager.get_all_data()
        except Exception:  # pragma: no cover - defensive
            return None
        raw = get_register_value(data.get("coil_1"))
        if raw is None:
            return None
        if raw == 1:
            return True
        if raw == 0:
            return False
        return None

    def _dhw_heatup_setpoint(manager) -> int | None:
        """Return the raw holding_16 register value, or None when unknown."""
        try:
            data = manager.get_all_data()
            register_data = data.get("holding_16")
        except Exception:  # pragma: no cover - defensive
            return None
        raw = get_register_value(register_data)
        if raw is None or is_unavailable_value(raw):
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        # Coordinator data is stored scaled (e.g. °C); convert back to the
        # raw register value expected by write_holding_register.
        scale = get_register_scale(register_data)
        try:
            scale = float(scale) if scale else 1.0
        except (TypeError, ValueError):
            scale = 1.0
        if scale == 0:
            scale = 1.0
        return round(value / scale)

    async def _run_dhw_single_heatup(
        hass,
        entry,
        manager,
        writer,
        target,
        timeout_s,
        hysteresis,
        restore_dhw_off,
        dhw_coil_name,
    ) -> None:
        """Background run: heat DHW once until target, timeout or cancel.

        Fires ``EVENT_DHW_SINGLE_HEATUP_FINISHED`` with the outcome and
        always leaves the request register cleared. Restores DHW to off
        when this run switched it on. Temperature decisions only use
        coordinator data that is fresh enough (see ``_DHW_MAX_DATA_AGE``).
        """
        config_entry_id = entry.entry_id
        outcome = "timeout"
        current = None
        data_stale = False
        data_age = None
        try:
            start = hass.loop.time()
            stale_warned = False
            while True:
                current = _dhw_temperature(manager)
                fresh = _dhw_temperature_is_fresh(manager)
                if fresh and current is not None and current >= target - hysteresis:
                    outcome = "reached"
                    break
                if not fresh and not stale_warned:
                    data_age = _dhw_temperature_age(manager)
                    _LOGGER.warning(
                        "DHW single heat-up for entry %s ignores stale "
                        "temperature data (age %s s, max %s s); waiting for "
                        "a fresh poll",
                        config_entry_id,
                        f"{data_age:.1f}" if data_age is not None else "unknown",
                        _DHW_MAX_DATA_AGE,
                    )
                    stale_warned = True
                elapsed = hass.loop.time() - start
                if elapsed >= timeout_s:
                    break
                await asyncio.sleep(
                    min(_DHW_RUN_STATUS_POLL_INTERVAL, timeout_s - elapsed)
                )
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        finally:
            data_age = _dhw_temperature_age(manager)
            data_stale = not _dhw_temperature_is_fresh(manager)
            failures = await _restore_dhw_heatup_state(
                hass,
                entry,
                writer,
                previous_setpoint=None,
                restore_setpoint=False,
                restore_dhw_off=restore_dhw_off,
                dhw_coil_name=dhw_coil_name,
            )
            _SINGLE_HEATUP_TASKS.pop(config_entry_id, None)
            if failures:
                # Keep the persisted state so a restart retries the restore.
                state = await _async_load_dhw_state(hass, config_entry_id)
                if state is not None:
                    state["restore_failed"] = True
                    try:
                        await _async_save_dhw_state(hass, config_entry_id, state)
                    except Exception as err:
                        _LOGGER.warning(
                            "Could not update DHW single heat-up recovery "
                            "state for entry %s: %s",
                            config_entry_id,
                            err,
                        )
            else:
                await _async_clear_dhw_state(hass, config_entry_id)
            hass.bus.async_fire(
                EVENT_DHW_SINGLE_HEATUP_FINISHED,
                {
                    "config_entry_id": config_entry_id,
                    "outcome": outcome,
                    "target_temperature": target,
                    "current_temperature": current,
                    "restore_failed": bool(failures),
                    "data_stale": data_stale,
                    "data_age_seconds": data_age,
                },
            )
            if failures:
                _LOGGER.error(
                    "DHW single heat-up for entry %s finished: %s but the "
                    "final restore failed - device state may be inconsistent "
                    "(target %s°C, now %s°C)",
                    config_entry_id,
                    outcome,
                    target,
                    current,
                )
            else:
                _LOGGER.info(
                    "DHW single heat-up for entry %s finished: %s (target %s°C, now %s°C)",
                    config_entry_id,
                    outcome,
                    target,
                    current,
                )

    async def async_start_dhw_single_heatup(call) -> None:
        """Heat DHW once to a target temperature with timeout (issue #21).

        Enables DHW when it is off, writes the setpoint, starts the
        request and returns immediately; a background task watches the
        DHW temperature, stops the request on target/timeout, restores
        DHW to off when this run switched it on, and fires
        ``EVENT_DHW_SINGLE_HEATUP_FINISHED``.

        The previous setpoint and DHW state are read from the device (with
        a cached fallback) before anything is written. If either is
        unknown, the service refuses to start so no modified setpoint can
        be left behind. The recovery state is persisted before the first
        write, so an interrupted run can be cleaned up after a restart.
        """
        hass = call.hass
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        target = float(call.data[ATTR_TARGET_TEMPERATURE])
        # Schema defaults only apply through HA's service layer; fall back
        # explicitly so direct handler calls stay valid too.
        timeout = call.data.get(ATTR_TIMEOUT, timedelta(hours=2))
        timeout_s = (
            timeout.total_seconds()
            if isinstance(timeout, timedelta)
            else float(timeout)
        )
        hysteresis = float(call.data.get(ATTR_HYSTERESIS, 0.5))

        entry = _get_entry_and_validate(hass, config_entry_id)
        runtime_data = entry.runtime_data
        manager = runtime_data.manager
        writer = runtime_data.coordinator.data_manager

        async with _single_heatup_lock(config_entry_id):
            running = _SINGLE_HEATUP_TASKS.get(config_entry_id)
            if running is not None and not running.done():
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="single_heatup_already_running",
                    translation_placeholders={"config_entry_id": config_entry_id},
                )

            # Resolve everything that must be restored BEFORE touching the
            # device. Unknown values abort the start without any write.
            previous_setpoint = await _resolve_dhw_heatup_setpoint(manager, writer)
            if previous_setpoint is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="single_heatup_setpoint_unknown",
                    translation_placeholders={"config_entry_id": config_entry_id},
                )

            dhw_coil_name = REGISTER_DHW_HVAC_MODE
            dhw_state = await _resolve_dhw_enabled(manager, writer)
            restore_dhw_off = dhw_state is False
            if dhw_state is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="single_heatup_dhw_state_unknown",
                    translation_placeholders={"config_entry_id": config_entry_id},
                )

            now = time.time()
            state = {
                "phase": "starting",
                "started_at": now,
                "deadline": now + timeout_s,
                "target": target,
                "timeout_s": timeout_s,
                "hysteresis": hysteresis,
                "restore_dhw_off": restore_dhw_off,
                "dhw_coil_name": dhw_coil_name,
                "previous_setpoint": previous_setpoint,
            }
            try:
                await _async_save_dhw_state(hass, config_entry_id, state)
            except Exception as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="write_failed",
                    translation_placeholders={
                        "operation_name": "save",
                        "register_type": "recovery state",
                        "register_name": "dhw_single_heatup",
                        "error": str(err),
                    },
                ) from err

            register_value = scaled_value_to_register(target, 0.01)
            try:
                if restore_dhw_off:
                    await _guarded_write(
                        REGISTER_DHW_HVAC_MODE,
                        lambda: writer.write_coil_register(dhw_coil_name, True),
                    )
                    _LOGGER.debug(
                        "Enabled DHW for single heat-up for entry %s",
                        config_entry_id,
                    )
                await _guarded_write(
                    "holding_16",
                    lambda: writer.write_holding_register("holding_16", register_value),
                )
                await _guarded_write(
                    "holding_15",
                    lambda: writer.write_holding_register("holding_15", 1),
                )
            except (Exception, asyncio.CancelledError):
                # Roll back every change already applied so a failed start
                # leaves the device in its previous state.
                failures = await _restore_dhw_heatup_state(
                    hass,
                    entry,
                    writer,
                    previous_setpoint=previous_setpoint,
                    restore_setpoint=True,
                    restore_dhw_off=restore_dhw_off,
                    dhw_coil_name=dhw_coil_name,
                )
                if not failures:
                    await _async_clear_dhw_state(hass, config_entry_id)
                raise

            state["phase"] = "running"
            try:
                await _async_save_dhw_state(hass, config_entry_id, state)
            except Exception as err:
                # The run is already active; do not fail the service, but
                # leave a trace because restart recovery is degraded.
                _LOGGER.warning(
                    "Could not persist running DHW single heat-up state for "
                    "entry %s: %s",
                    config_entry_id,
                    err,
                )

            task = hass.async_create_task(
                _run_dhw_single_heatup(
                    hass,
                    entry,
                    manager,
                    writer,
                    target,
                    timeout_s,
                    hysteresis,
                    restore_dhw_off,
                    dhw_coil_name,
                ),
                name=f"{DOMAIN}_dhw_single_heatup_{config_entry_id}",
            )
            _SINGLE_HEATUP_TASKS[config_entry_id] = task
            if task.done():
                # Eager task already finalized before registration (stop
                # written, event fired); drop the stale handle.
                _SINGLE_HEATUP_TASKS.pop(config_entry_id, None)
        _LOGGER.debug(
            "Started DHW single heat-up to %s°C for entry %s (timeout %ss)",
            target,
            config_entry_id,
            timeout_s,
        )

    async def async_cancel_single_heatup(config_entry_id: str) -> None:
        """Cancel a running DHW single heat-up, if any (used on unload)."""
        async with _single_heatup_lock(config_entry_id):
            task = _SINGLE_HEATUP_TASKS.pop(config_entry_id, None)
            if task is None or task.done():
                return
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as err:
                _LOGGER.debug(
                    "DHW single heat-up task for entry %s ended with: %s",
                    config_entry_id,
                    err,
                )

    async def async_recover_dhw_single_heatup(hass, entry) -> None:
        """Recover an interrupted DHW single heat-up after a restart.

        Called during setup. If the persisted run is still active and its
        deadline has not passed, the background monitor is resumed.
        Otherwise the request and any partially applied changes are
        rolled back. A failed restore keeps the persisted state and raises
        a repair issue so the next start retries it.
        """
        config_entry_id = entry.entry_id
        state = await _async_load_dhw_state(hass, config_entry_id)
        if not state:
            return

        runtime_data = getattr(entry, "runtime_data", None)
        if runtime_data is None:
            return
        manager = runtime_data.manager
        writer = runtime_data.coordinator.data_manager

        async with _single_heatup_lock(config_entry_id):
            running = _SINGLE_HEATUP_TASKS.get(config_entry_id)
            if running is not None and not running.done():
                return

            phase = state.get("phase")
            try:
                target = float(state.get("target", 0) or 0)
                hysteresis = float(state.get("hysteresis", 0.5) or 0.5)
                deadline = float(state.get("deadline", 0) or 0)
            except (TypeError, ValueError):
                _LOGGER.warning(
                    "Ignoring corrupt DHW single heat-up recovery state for entry %s",
                    config_entry_id,
                )
                await _async_clear_dhw_state(hass, config_entry_id)
                return

            previous_setpoint = state.get("previous_setpoint")
            restore_dhw_off = bool(state.get("restore_dhw_off", False))
            dhw_coil_name = state.get("dhw_coil_name") or REGISTER_DHW_HVAC_MODE
            now = time.time()

            active = None
            reader = getattr(writer, "read_holding_register", None)
            if callable(reader):
                try:
                    active = await reader("holding_15")
                except Exception as err:
                    _LOGGER.warning(
                        "Could not read DHW heat-up request state during "
                        "recovery for entry %s: %s",
                        config_entry_id,
                        err,
                    )
            if active is None:
                active = _dhw_heatup_request_active(manager)

            # Verify the device still holds the state this run left behind
            # before restoring anything. A user (or the device itself) may
            # have changed the setpoint while Home Assistant was down;
            # overwriting that change would destroy user intent. The
            # expected value is the raw register value the run wrote,
            # derived from the persisted target.
            expected_setpoint = scaled_value_to_register(target, 0.01)
            current_setpoint = None
            if callable(reader):
                try:
                    current_setpoint = await reader("holding_16")
                except Exception as err:
                    _LOGGER.debug(
                        "Could not read DHW setpoint during recovery for entry %s: %s",
                        config_entry_id,
                        err,
                    )
            try:
                current_setpoint = (
                    int(current_setpoint) if current_setpoint is not None else None
                )
            except (TypeError, ValueError):
                current_setpoint = None

            if current_setpoint is None:
                setpoint_restore = "unknown"
            elif current_setpoint == expected_setpoint:
                setpoint_restore = "ours"
            elif previous_setpoint is not None and current_setpoint == int(
                previous_setpoint
            ):
                # The run's setpoint write never landed (or was already
                # reverted); nothing to restore for this register.
                setpoint_restore = "already_restored"
            else:
                setpoint_restore = "changed"

            if setpoint_restore == "changed":
                _LOGGER.info(
                    "DHW setpoint for entry %s changed while Home Assistant "
                    "was down (expected %s, found %s); skipping setpoint "
                    "and DHW-state restore to preserve the user change",
                    config_entry_id,
                    expected_setpoint,
                    current_setpoint,
                )

            if (
                phase == "running"
                and active != 0
                and deadline > now
                and target > 0
                and setpoint_restore == "ours"
            ):
                remaining = deadline - now
                _LOGGER.info(
                    "Resuming DHW single heat-up for entry %s after restart "
                    "(target %s°C, %.0fs remaining)",
                    config_entry_id,
                    target,
                    remaining,
                )
                task = hass.async_create_task(
                    _run_dhw_single_heatup(
                        hass,
                        entry,
                        manager,
                        writer,
                        target,
                        remaining,
                        hysteresis,
                        restore_dhw_off,
                        dhw_coil_name,
                    ),
                    name=f"{DOMAIN}_dhw_single_heatup_{config_entry_id}",
                )
                _SINGLE_HEATUP_TASKS[config_entry_id] = task
                if task.done():
                    _SINGLE_HEATUP_TASKS.pop(config_entry_id, None)
                return

            _LOGGER.info(
                "Cleaning up interrupted DHW single heat-up for entry %s "
                "(phase %s, request %s)",
                config_entry_id,
                phase,
                active,
            )
            failures = await _restore_dhw_heatup_state(
                hass,
                entry,
                writer,
                previous_setpoint=previous_setpoint,
                # A partially started run may have overwritten the setpoint;
                # a completed run intentionally leaves the target setpoint.
                # The write only happens when the device still holds the
                # value this run wrote - never over a user change.
                restore_setpoint=(phase != "running" and setpoint_restore == "ours"),
                # The DHW-off restore is skipped when the setpoint proves
                # the user took over the device while HA was down.
                restore_dhw_off=restore_dhw_off and setpoint_restore != "changed",
                dhw_coil_name=dhw_coil_name,
            )
            if setpoint_restore == "unknown" and phase != "running":
                # The setpoint could not be verified, so restoring it
                # blindly could overwrite a user change. Keep the recovery
                # state and raise a repair issue so the next start retries.
                failures.append("setpoint verification failed")
                async_create_dhw_heatup_restore_issue(hass, entry, "; ".join(failures))
            if failures:
                _LOGGER.warning(
                    "Could not fully restore DHW state for entry %s after "
                    "restart; recovery state kept for the next start",
                    config_entry_id,
                )
            else:
                await _async_clear_dhw_state(hass, config_entry_id)

else:  # pragma: no cover - dummies only without Home Assistant
    # Dummy functions for testing imports
    async def async_set_operation_mode(call):
        pass

    async def async_set_dhw_state(call):
        pass

    async def async_set_main_zone_state(call):
        pass

    async def async_set_additional_zone_state(call):
        pass

    async def async_set_smart_grid_mode(call):
        pass

    async def async_set_quiet_mode(call):
        pass

    async def async_set_dhw_booster_mode(call):
        pass

    async def async_set_dhw_single_heatup(call):
        pass

    async def async_start_dhw_single_heatup(call):
        pass

    async def async_cancel_single_heatup(config_entry_id: str):
        pass

    async def async_recover_dhw_single_heatup(hass, entry):
        pass

    async def async_set_power_limit(call):
        pass

    async def async_set_heating_offset(call):
        pass

    async def async_set_cooling_offset(call):
        pass

    async def async_set_room_heating_setpoint(call):
        pass

    async def async_set_room_cooling_setpoint(call):
        pass

    async def async_set_additional_zone_setpoint(call):
        pass

    async def async_refresh_connection(call):
        pass


def register_services(hass) -> None:
    """Register integration services."""
    if not HAS_HA:
        return
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_OPERATION_MODE,
        async_set_operation_mode,
        schema=SERVICE_SET_OPERATION_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_DHW_STATE,
        async_set_dhw_state,
        schema=SERVICE_SET_DHW_STATE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_MAIN_ZONE_STATE,
        async_set_main_zone_state,
        schema=SERVICE_SET_MAIN_ZONE_STATE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ADDITIONAL_ZONE_STATE,
        async_set_additional_zone_state,
        schema=SERVICE_SET_ADDITIONAL_ZONE_STATE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_SMART_GRID_MODE,
        async_set_smart_grid_mode,
        schema=SERVICE_SET_SMART_GRID_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_QUIET_MODE,
        async_set_quiet_mode,
        schema=SERVICE_SET_QUIET_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_DHW_BOOSTER_MODE,
        async_set_dhw_booster_mode,
        schema=SERVICE_SET_DHW_BOOSTER_MODE_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_DHW_SINGLE_HEATUP,
        async_set_dhw_single_heatup,
        schema=SERVICE_SET_DHW_SINGLE_HEATUP_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_START_DHW_SINGLE_HEATUP,
        async_start_dhw_single_heatup,
        schema=SERVICE_START_DHW_SINGLE_HEATUP_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_POWER_LIMIT,
        async_set_power_limit,
        schema=SERVICE_SET_POWER_LIMIT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_HEATING_OFFSET,
        async_set_heating_offset,
        schema=SERVICE_SET_HEATING_OFFSET_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_COOLING_OFFSET,
        async_set_cooling_offset,
        schema=SERVICE_SET_COOLING_OFFSET_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ROOM_HEATING_SETPOINT,
        async_set_room_heating_setpoint,
        schema=SERVICE_SET_ROOM_HEATING_SETPOINT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ROOM_COOLING_SETPOINT,
        async_set_room_cooling_setpoint,
        schema=SERVICE_SET_ROOM_COOLING_SETPOINT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_ADDITIONAL_ZONE_SETPOINT,
        async_set_additional_zone_setpoint,
        schema=SERVICE_SET_ADDITIONAL_ZONE_SETPOINT_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_REFRESH_CONNECTION,
        async_refresh_connection,
        schema=SERVICE_REFRESH_CONNECTION_SCHEMA,
    )
    _LOGGER.debug("Registered Daikin Altherma 4 Modbus services")
