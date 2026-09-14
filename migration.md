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

- [x] Add `modbus-connection[pymodbus]` to `manifest.json` requirements
      (alongside `pymodbus` until Phase 5)
- [x] Implement a `ModbusUnit` facade behind the existing
      `modbus/client_interface.py`: adapter translates 1-based Daikin
      addresses to 0-based raw addresses and maps `ModbusError` hierarchy to
      the integration's exception types
- [x] Unit tests for the facade: address translation, error mapping, special
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
    params: ModbusParams,  # ModbusTcpParams | ModbusUdpParams | ModbusTlsParams | ModbusSerialParams
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

Phase 3 is broken into small, independently verifiable steps so the
production path stays green at every point. Each step keeps its own
verification (tests + `ruff`) before moving on.

- [x] **3.1 — Thread `hass`/`entry`/`unit_id` through the stack** (structural,
      no behavior change): extend `ModbusDataManager` and
      `ModbusTransportSession` with optional connection-identity fields so
      existing `ModbusDataManager(host, port, demo_mode)` call sites and tests
      keep working. Verify: full suite green, `ruff` clean.
- [x] **3.2 — Add an HA-backed unit provider** (parallel path, not yet active):
      a function in `connection_manager` that calls `async_get_unit` (from
      `homeassistant.components.modbus`) and wraps the returned unit in a
      `ModbusConnectionClient`. Covered by a focused test mocking HA's
      `async_get_unit`.
- [x] **3.3 — Switch `ModbusTransportSession` to the new path** (demo mode
      kept): in `ensure_connection()`, when `hass`/`entry` are set and not
      demo mode, obtain the client via the HA-backed provider (lazy, no I/O);
      otherwise fall back to `RealModbusTcpClient`. `reconnect_with_new_client`
      must not recreate a shared connection — `async_get_unit` returns the same
      shared unit. Verify: existing session/repository/data-manager tests plus
      a new sharing test.
- [x] **3.4 — Remove the own connection cache from `RealModbusTcpClient`:**
      drop `_client_cache`, `_client_locks`, `_cache_lock`, `clear_cache`,
      `safe_clear_cache`, `async_close_cached_client`, and the `create`
      factory; the client holds one instance per session. Update the
      `__init__.py` call sites that used them.
- [x] **3.5 — Rework setup / unload / config-flow logic:** in `__init__.py`,
      replace the `create`+`connect` probe and `async_close_cached_client`
      with `async_get_temporary_unit` + a first read (or lazy `async_get_unit`),
      keep `ConfigEntryNotReady` only for structural/setup failures (no
      reload on transient drops); unload relies on HA lifecycle. Port
      `config_flow._test_connection` to the new path. Verify: integration
      tests (`test_integration_lifecycle`, `test_demo_mode_installation`,
      `test_unload_shared_endpoint`).

      Implementation notes:
      - `connection_manager.async_test_connection_with_temporary_unit(hass,
        host, port, unit_id)` probes via `async_get_temporary_unit` +
        `read_input_registers(1, 1)`; always returns a
        `(ok, "cannot_connect")` tuple (never raises through).
      - `config_flow._test_connection(hass, host, port, unit_id)` and the
        repair flow now pass the configured `unit_id`; setup (`__init__.py`)
        reuses the same `_test_connection` seam so one probe serves flows,
        setup, and the real-HA tests.
      - Unload/setup-failure no longer closes any cached client — the HA
        component owns the shared connection lifecycle;
        `ModbusConnectionClient.disconnect()` is a no-op for HA-owned units.
      - Guarded import: HA 2026.8 (current dev env) has neither
        `async_get_unit` nor `async_get_temporary_unit`; the provider flag
        `_HAS_SHARED_UNIT_PROVIDER` degrades gracefully — the probe reports
        `cannot_connect` and the HA-backed unit path raises a clear
        `ModbusConnectionException` until the HA 2026.9 runtime is used
        (Docker E2E / production).
- [x] **3.6 — Cleanup & dependency check:** verify whether `manifest.json`
      still needs `modbus-connection` directly once HA's `modbus` component is
      the provider; check remaining direct `pymodbus` usage; consolidate
      now-redundant tests/code.

      Verification results:
      - **`manifest.json` requirements:** both libraries remain required for
        now — `modbus-connection` directly (production imports
        `ModbusTcpParams` in `connection_manager` and `ModbusConnection` +
        the exception hierarchy in the facade), and `pymodbus` at runtime via
        the `[pymodbus]` extra (which requires `pymodbus[serial]>=3.11`,
        superseding the old separate `pymodbus>=3.8` pin). The redundant
        standalone `pymodbus>=3.8` entry was dropped; Phase 5 re-evaluates
        both once the legacy client is removed.
      - **Direct `pymodbus` usage:** confined to the legacy
        `modbus/modbus_client.py` (`AsyncModbusTcpClient`, `ModbusError*`),
        used only by the non-HA-backed fallback path (`ensure_modbus_connection`)
        and demo mode. Removed at the Phase 5 cutover.
      - **Test consolidation:**
        - `tests/modbus/test_connection_pool.py` deleted — it exercised the
          integration's own connection cache removed in 3.4 by driving a
          test-local mock with timing/flakiness-prone assertions and contained
          a `test_connection_pool_cache_management_concept` that literally
          tested nothing. Replaced by `test_ensure_modbus_connection.py`
          (client creation real/demo, reuse, lazy reconnect, failure
          propagation).
        - `tests/integration/test_config_flow.py`: removed dead
          `_FakeModbusClient`/`_FakeModbusClientReadError` and leftover
          `RealModbusTcpClient.connect`/`__init__` patches that no seam
          reaches; added a probe-exception → `cannot_connect` test through the
          real `connection_manager` boundary.
        - Test isolation: `test_unload_shared_endpoint.py` snapshots and
          restores `sys.modules` for the `homeassistant*`/`custom_components*`
          namespaces (fixes the poisoning reported in 3.5 — later real-HA
          setup tests see `ConfigEntryNotReady` instead of a plain
          `Exception`). A `config_flow`-level quirk remains: HA's flow
          manager instantiates the handler from a fresh module re-imported
          after the test-suite re-imports the package under stubs, so
          module-level patches on the collector's module copy have no effect.
          That ordering sensitivity is pre-existing (verified identical on
          the base commit) and out of scope for 3.6.

### Phase 4 — Data manager, read & write paths

- [x] Port `core/data_manager.py` read batching to unit reads (flat lists,
      no `is_error()` handling)
- [x] Translate pymodbus-style error handling to the `ModbusError` hierarchy
      at exactly one boundary
- [x] Writes: keep raw-value assertions (address + raw value + function code)
- [x] Coordinator regression: normal/slow/unified behavior unchanged

      Implementation notes:
      - `core/mapping_transform.py`: `process_register_block` accepts flat
        `list` unit reads (index `address - offset`) alongside legacy
        `.registers` responses; `process_bit_sensors` accepts flat
        `list[bool]` (index `address - 1`, reads start at 1) alongside
        legacy `.bits`. Flat lists never carry an error state.
      - `modbus/register_repository.py`: new `_is_error_result` helper —
        flat lists/`None` are always success, legacy response objects keep
        the `isError()` classification until the Phase 5 cutover.
        `ModbusInvalidAddressException` (from `IllegalDataAddressError`) is
        now a first-class case: input reads degrade to `[]`,
        discrete/coils to `None`, holding falls back to chunked blocks —
        all without spending a reconnect retry. Transient failures still
        retry once. `_READ_EXCEPTIONS`/`_WRITE_EXCEPTIONS` include the new
        type; the `exception_code=` string parsing stays legacy-only.
      - Writes: `None` unit returns (`write_register`/`write_coil` contract)
        are normalized to `True` so the callers' `is not None` success
        checks work on both paths; address + raw value are passed through
        unchanged (FC06/FC05 asserted in the facade tests).
      - `modbus/modbus_connection_client.py`: single translation boundary
        hardened — `_MODBUS_ERROR_TYPES` tuple keeps the `except` clause
        valid when `modbus-connection` is not installed.
      - `integration/coordinator.py`: `_COORDINATOR_IO_EXCEPTIONS` includes
        `ModbusInvalidAddressException`, so an unsupported range becomes
        `UpdateFailed` (repair issue) instead of an unhandled crash.
      - `modbus/transport_session.py`: `is_modbus_error` returns `False`
        for flat lists/`None` explicitly (legacy helper kept to Phase 5).
      - New tests `tests/modbus/test_register_repository_flat_lists.py`
        (11 tests: flat batch reads, mapping on flat lists, invalid-address
        degradation without retry, transient retry, `None`-write success,
        invalid-address write propagation).

      Verification results:
      - `pytest`: **504 passed, 1 deselected** (Docker E2E opt-in) —
        includes the 11 new Phase-4 tests plus all pre-existing
        repository-batching/write, facade (address + raw value + FC),
        mapping, and coordinator suites unchanged and green.
      - End-to-end probe against `MockModbusConnection`: input batch
        (21, 67) + holding batch (1, 80) + discrete (1, 26) + coils (1, 3)
        through repository + mapping yield 84 mapped keys; writes land at
        raw 8 / raw 0 with FC `0x06`/`0x05`; special value `32767` passes
        through; `IllegalDataAddressError` surfaces as
        `ModbusInvalidAddressException` and degrades to `[]`.
      - `ruff check .` / `ruff format --check .`: clean.

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
- **HA version gate:** the shared-unit helpers (`async_get_unit`,
  `async_get_temporary_unit`) only exist from HA 2026.9. On HA 2026.8 the
  probe reports `cannot_connect` and the HA-backed data path raises
  `ModbusConnectionException`; real-device operation requires the HA 2026.9
  runtime (Phase 6 Docker E2E validates this against HA stable).
- pymodbus remains the transport backend (via the extra), so wire behavior
  should be identical — but addressing and exception semantics are exactly
  what the Phase 0 spikes pin down.
- HA 2026.9 breaking changes were reviewed against this integration: none
  apply (no `modbus.get_hub` usage, no device-registry deprecations in use).
