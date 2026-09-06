# Modbus Connection Migration

Status and plan for migrating this integration from its own `pymodbus`-based
client to Home Assistant's `modbus-connection` library
(HA 2026.9 "Modernizing Modbus" direction).

- Development branch: `feat/modbus-connection-migration`
- Reference library: `modbus-connection` 4.10.0 (`modbus-connection[pymodbus]`)
- Introduced in: config entry `VERSION 2` (unit_id), manifest `0.7.0-dev`

---

## 1. Goal

```
Before                                   After (target)
─────────────────────────────────────    ─────────────────────────────────────
integration → own ModbusTcpClient        integration → thin facade
              → pymodbus                             → modbus_connection.ModbusUnit
                                                       (shared per host:port)
```

Multiple integrations can share one physical connection: `ModbusUnit` is
obtained per `(host, port)` connection and addressed via `unit_id`. This
integration keeps its own register model, parsing, coordinators, and entities
unchanged — only the transport boundary moves.

## 2. Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend | `modbus-connection[pymodbus]` (not `tmodbus` directly) | HA-provided abstraction; pymodbus remains the transport under the hood |
| `unit_id` storage | Config entry `data` (not `options`) | Connection identity, like `host`/`port`; two entries with the same `(host, port)` but different units are distinct devices |
| Migration | `async_migrate_entry` v1→v2, automatic, idempotent | No user reconfiguration required; existing installs keep working |
| Rollout | No feature toggle — single path after spikes pass | Avoid maintaining two transports; spikes de-risk the switch |
| Register addressing | Keep 1-based Daikin register definitions; facade translates `address - 1` | Register constants are the source of truth and must not change |
| Special values 32765/32766/32767 | Pass through raw; interpretation stays in the integration | Register semantics belong to the data layer, not the transport |
| Shared connection | Real use case: other integrations use the same connection | Keyed by `(host, port)`; `unit_id` selects the unit |

## 3. Spike findings (Phase 0)

Executable documentation in `tests/modbus/test_modbus_connection_compat.py`
(skipped automatically when `modbus-connection` is not installed):

- **Addressing:** `ModbusUnit` raw API is 0-based, same as pymodbus. Reading at
  the untouched 1-based address silently returns the wrong register — the
  `address - 1` translation is a hard contract for the facade.
- **Reads:** return a flat `list[int]`; there is no response object and no
  `is_error()` / `.registers` indirection.
- **Special values:** `32765` / `32766` / `32767` pass through untouched.
- **Errors:** failures raise the `ModbusError` hierarchy
  (e.g. `IllegalDataAddressError`) instead of returning error responses.
- **Writes:** `write_register` / `write_coil` map to FC06 / FC05
  (FC16 / FC15 for multi-value variants).

## 4. Current state (Phase 0 & 1 complete)

### Done

- [x] **Phase 0 — spikes** against the `modbus_connection` mock backend:
      addressing, special values, error model, write function codes
      (`tests/modbus/test_modbus_connection_compat.py`)
- [x] **Phase 1 — `unit_id` in the config model:**
      - `core/const.py`: `CONF_UNIT_ID`, `DEFAULT_UNIT_ID = 1`
      - `integration/config_flow.py`: `VERSION = 2`, `MINOR_VERSION = 1`;
        `unit_id` field (default 1, validated 1–247, error `invalid_unit_id`)
        in user / reconfigure / reauth steps; entry data includes `unit_id`
      - `__init__.py`: `async_migrate_entry` v1→v2 — idempotent, adds
        `unit_id: 1`, preserves all existing data/options
      - `integration/repair_flow.py`: preserves `unit_id`
      - `translations/en.json` + `de.json`: field descriptions (all three
        flows) and `invalid_unit_id` error message
      - `manifest.json`: version → `0.7.0-dev`
- [x] **Regression test** `tests/ha/test_config_entry_migration.py`
      (v1 entry → migrated with default, reload-stable, idempotent)
- [x] **Test adjustments:** data assertions now expect `unit_id`
      (`test_config_flow.py`), const/voluptuous stubs extended
      (`test_config_model.py`, `test_config_flow_data_description.py`)

### Validation status

- `pytest`: **470 passed, 1 deselected** (Docker E2E test, opt-in via
  `HA_DOCKER_DEMO_TESTS=1`)
- `ruff check .` / `ruff format --check .`: clean
- pre-commit: `safety` passed; `bandit` fails with an environment error
  (`pbr` missing, Python 3.14 env) — not code-related

### Known gaps / notes

- `translations/nl.json` does not contain the new `unit_id` strings; HA falls
  back to English (optional follow-up).
- `manifest.json` still requires `pymodbus>=3.8` — intentional; the backend
  swap happens in Phase 2/3.
- The Docker E2E test still writes version-1 entry data on purpose: it
  exercises exactly the migration path of real existing installs.

## 5. Further phases

### Phase 2 — Facade & dependency

- [ ] Add `modbus-connection[pymodbus]` to `manifest.json` requirements
      (alongside `pymodbus` until Phase 5)
- [ ] Implement a `ModbusUnit` facade behind the existing
      `modbus/client_interface.py`: adapter translates 1-based Daikin
      addresses to 0-based raw addresses and maps `ModbusError` hierarchy to
      the integration's exception types
- [ ] Unit tests for the facade: address translation, error mapping, special
      value passthrough, write function-code mapping

### Phase 3 — Connection lifecycle on the shared unit

`async_get_unit` is a Home Assistant component API imported from
`homeassistant.components.modbus` (not from the standalone
`modbus-connection` PyPI package). **Confirmed present in the target version
HA 2026.9** (verified against the `2026.9.0` tag of `home-assistant/core`):
it is defined in `homeassistant/components/modbus/connection.py` and
re-exported via `__all__` in that component's `__init__.py`.

Actual signature (from the `2026.9.0` source, `connection.py`):

```python
@callback
def async_get_unit(
    hass: HomeAssistant,
    entry: ConfigEntry,
    params: ModbusParams,   # ModbusTcpParams | ModbusUdpParams | ModbusTlsParams | ModbusSerialParams
    unit_id: int,
) -> ModbusUnit: ...
```

Usage:

```python
from homeassistant.components.modbus import async_get_unit
from modbus_connection import ModbusTcpParams

unit = async_get_unit(
    hass,
    entry,
    ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
    entry.data[CONF_UNIT_ID],
)
```

Key details confirmed from the `2026.9.0` source:

- **`async_get_unit` is synchronous and `@callback`** — it performs **no I/O**
  and makes no awaitable call. The first read opens the link; a dropped link
  reopens on the next request. **Do not reload the entry when a connection
  drops** — `ConfigEntryNotReady` must *not* be raised for a transient
  connection loss.
- **Lifecycle sharing is implemented in the component**: a `_SharedConnection`
  holds the `ModbusConnection` plus a `consumers` counter, keyed by the
  endpoint `(host, port)` and gated on identical `params`. `async_get_unit`
  increments the count and registers `entry.async_on_unload(release)`; the
  connection closes when the **last** holder's entry unloads. `unit_id`
  selects the unit via `connection.for_unit(unit_id)`.
- A device **already in use under different link settings** raises
  `HomeAssistantError` (one connection cannot honour two baud rates).
- The HA component imports `ModbusTcpParams` and `ModbusUnit` from the
  standalone `modbus_connection` library — so the library version we pin must
  be API-compatible with what the HA component expects.
- `async_get_temporary_unit(hass, params, unit_id)` (async context manager)
  exists alongside for config flows that have no config entry yet.

Port accordingly:

- [ ] Port `modbus/connection_manager.py` and `modbus/transport_session.py`
      to `async_get_unit` (import from `homeassistant.components.modbus`)
- [ ] Connection sharing is handled by HA; drop our own `(host, port)` cache
      and rely on `unit_id` selecting the unit
- [ ] Keep the entry loaded across connection drops (no `ConfigEntryNotReady`
      on transient loss); reserve it for setup-time failures
- [ ] Tests: connect failure, reconnect, unload cleanup, two entries sharing
      one `(host, port)` with different `unit_id` values

### Phase 4 — Data manager, read & write paths

- [ ] Port `core/data_manager.py` read batching to unit reads (flat lists,
      no `is_error()` handling)
- [ ] Translate pymodbus-style error handling to the `ModbusError` hierarchy
      at exactly one boundary
- [ ] Writes: keep raw-value assertions (address + raw value + function code)
- [ ] Coordinator regression: normal/slow/unified behavior unchanged

### Phase 5 — Cutover & cleanup

- [ ] Switch the client default to the facade; remove the legacy
      `pymodbus`-direct client path (no feature toggle, per decision)
- [ ] Drop the direct `pymodbus` requirement from `manifest.json` if nothing
      else needs it
- [ ] Promote `tests/modbus/test_modbus_connection_compat.py` from
      `importorskip` to a regular suite test

### Phase 6 — Hardening & documentation

- [ ] Docker E2E (`HA_DOCKER_DEMO_TESTS=1`) against HA stable, including the
      v1→v2 migration of its fixture entry
- [ ] Update `README.md`, `SCRIPTS.md`, and the Cline rules (`20-modbus`) for
      the new backend
- [ ] Optional: add `unit_id` strings to `translations/nl.json`
- [ ] Final version bump `0.7.0-dev` → `0.7.0` on release

## 6. Risks / watch items

- `modbus-connection` is young; its API may still shift. Keep the facade thin
  so library changes stay localized.
- pymodbus remains the transport backend (via the extra), so wire behavior
  should be identical — but addressing and exception semantics are exactly
  what the Phase 0 spikes pin down.
- HA 2026.9 breaking changes were reviewed against this integration: none
  apply (no `modbus.get_hub` usage, no device-registry deprecations in use).
