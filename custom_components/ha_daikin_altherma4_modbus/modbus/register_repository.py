"""Register-repository layer for Modbus register access."""

import asyncio
import logging
import time
from typing import Any

from ..common.helpers import get_register_config, to_signed_16bit
from ..core.const import MAX_MODBUS_ADDRESS, MIN_MODBUS_ADDRESS
from ..core.exceptions import (
    ModbusConnectionException,
    ModbusDeviceException,
    ModbusInvalidAddressException,
    ModbusReadException,
    ModbusTimeoutException,
    ModbusWriteException,
)
from .transport_session import ModbusTransportSession

_LOGGER = logging.getLogger(__name__)


def _validate_modbus_address(address: int, context: str = "address") -> int:
    """
    Validate and clamp Modbus address to valid range based on device documentation.

    Args:
        address: The address to validate
        context: Context description for error messages

    Returns:
        Validated address clamped to device-specific range (1-87)

    Raises:
        ValueError: If address is not a valid integer
    """
    if not isinstance(address, int):
        raise TypeError(
            f"Invalid {context}: must be integer, got {type(address).__name__}"
        )

    if address < MIN_MODBUS_ADDRESS or address > MAX_MODBUS_ADDRESS:
        _LOGGER.warning(
            f"Modbus {context} {address} is outside valid device range ({MIN_MODBUS_ADDRESS}-{MAX_MODBUS_ADDRESS}), clamping"
        )
        address = max(MIN_MODBUS_ADDRESS, min(MAX_MODBUS_ADDRESS, address))

    return address


_READ_EXCEPTIONS = (
    ModbusReadException,
    ModbusTimeoutException,
    ModbusDeviceException,
    ModbusConnectionException,
    ModbusInvalidAddressException,
    asyncio.TimeoutError,
    OSError,
    ConnectionError,
)
_WRITE_EXCEPTIONS = (
    ModbusWriteException,
    ModbusTimeoutException,
    ModbusDeviceException,
    ModbusConnectionException,
    ModbusInvalidAddressException,
    asyncio.TimeoutError,
    OSError,
    ConnectionError,
)

# Register-map versions (Configuration reference guide 4P773396):
# "v2/v3" (MMI v2/v3, guide revisions 1B/1C) exposes discrete input 26
# ("Imposed limit acceptance"); "v4" (MMI v4.x, revision 1D) drops it
# and adds holding 81 plus input 138/139 instead.
REGISTER_MAP_V2_V3 = "v2/v3"
REGISTER_MAP_V4 = "v4"

# Human-readable source of each register map for log lines.
_REGISTER_MAP_SOURCES = {
    REGISTER_MAP_V2_V3: "MMI v2/v3, guide 4P773396-1B/1C",
    REGISTER_MAP_V4: "MMI v4.x, guide 4P773396-1D",
}

# Optimized batch layout shared by the polling path and raw snapshots.
_INPUT_BATCH = (21, 67)
_HOLDING_BATCH = (1, 80)
# v4 devices (MMI v4.x, guide revision 1D) add holding 81 (execute model
# restart), so the batch grows to 1-81 once input 138/139 proved present.
_HOLDING_BATCH_V4 = (1, 81)
_HOLDING_FALLBACK_BLOCKS = ((1, 25), (26, 25), (51, 30))
# v4-only holding register as a single read for the fallback path.
_HOLDING_V4_FALLBACK_BLOCK = (81, 1)
_DISCRETE_BATCH = (1, 26)
# v4 devices (MMI v4.x, guide revision 1D) no longer expose discrete
# input 26, so the batch shrinks to 1-25 once that is detected.
_DISCRETE_BATCH_V4 = (1, 25)
_COILS_BATCH = (1, 3)
# v4-only input registers: time until model restart + active operation
# state (maintenance / restart pending).
_INPUT_V4_BATCH = (138, 2)


def _raw_registers(result: Any, raw_start: int) -> dict[int, int]:
    """Normalize a register read to a raw 0-based address map.

    Flat unit lists start at the requested (1-based) address, so
    ``raw_start`` is that address minus one. Legacy 1-based response arrays
    carry the absolute address as their index, i.e. raw address ``index - 1``.
    """
    if isinstance(result, (list, tuple)):
        return {raw_start + index: int(value) for index, value in enumerate(result)}
    registers = getattr(result, "registers", None) or []
    return {
        index - 1: int(value)
        for index, value in enumerate(registers)
        if index - 1 >= raw_start
    }


def _raw_bits(result: Any, raw_start: int) -> dict[int, bool]:
    """Normalize a bit read to a raw 0-based address map (see above)."""
    if isinstance(result, (list, tuple)):
        return {raw_start + index: bool(value) for index, value in enumerate(result)}
    bits = getattr(result, "bits", None) or []
    return {
        index - 1: bool(value)
        for index, value in enumerate(bits)
        if index - 1 >= raw_start
    }


def _is_error_result(session: ModbusTransportSession, result: Any) -> bool:
    """Classify a read/write result as a device error.

    Flat ``list``/``tuple`` unit reads (``ModbusConnectionClient``) never
    carry an error state — failures raise at the facade boundary instead.
    Response objects (demo ``MockModbusTcpClient``, test fakes) with
    ``isError()``/``is_error()`` keep the legacy classification.
    """
    if result is None or isinstance(result, (list, tuple)):
        return False
    is_modbus_error = getattr(session, "is_modbus_error", None)
    if callable(is_modbus_error):
        try:
            return bool(is_modbus_error(result))
        except Exception:  # pragma: no cover - defensive
            return False
    return bool(ModbusTransportSession.is_modbus_error(result))


class ModbusRegisterRepository:
    """Reads and writes Modbus registers for configured blocks."""

    def __init__(self, session: ModbusTransportSession):
        self._session = session
        # Version-detection caches (None = not probed yet). They live on the
        # repository (not the client) so they survive reconnects.
        self._supports_discrete_26: bool | None = None
        self._supports_input_138_139: bool | None = None
        # Holding 81 (v4-only "execute model restart") is learned lazily
        # from polling: None = not attempted yet, True = present (batch
        # 1-81), False = refused (batch stays 1-80). Unlike the two probes
        # above it never feeds register_version, only the batch layout.
        self._supports_holding_81: bool | None = None
        self._last_logged_version: str | None = None

    @property
    def register_version(self) -> str | None:
        """Detected register-map version ("v2/v3"/"v4") or None if unknown.

        "v2/v3" (MMI v2/v3, guide revisions 1B/1C) exposes discrete input 26
        while "v4" (MMI v4.x, revision 1D) drops it and adds holding 81 plus
        input 138/139 instead. Ambiguous or partially probed states report
        None rather than guessing.
        """
        if self._supports_discrete_26 and not self._supports_input_138_139:
            return REGISTER_MAP_V2_V3
        if self._supports_input_138_139 and not self._supports_discrete_26:
            return REGISTER_MAP_V4
        return None

    def _discrete_batch(self) -> tuple[int, int]:
        """Discrete-input batch honoring the detected register map.

        Version-specific register 26 is only polled once the v2/v3 map is
        confirmed; on v4 — and while the map is still unknown (fallback) —
        the batch stays at 1-25 so no absent register is requested.
        """
        if self._supports_discrete_26 is True:
            return _DISCRETE_BATCH
        return _DISCRETE_BATCH_V4

    def _holding_batch(self) -> tuple[int, int]:
        """Holding-register batch honoring the detected register map.

        Version-specific register 81 (execute model restart) only exists
        on v4. It is attempted once input 138/139 proved the v4 map (or a
        previous 1-81 read succeeded); on v2/v3, after a refusal, and
        while the map is still unknown (fallback) the batch stays at 1-80
        so no absent register is requested.
        """
        if self._supports_holding_81 is False:
            return _HOLDING_BATCH
        if self._supports_holding_81 is True or self._supports_input_138_139 is True:
            return _HOLDING_BATCH_V4
        return _HOLDING_BATCH

    async def _probe_register(self, kind: str, address: int, count: int) -> bool | None:
        """Probe whether version-discriminating register(s) exist.

        Returns True when the read succeeds, False when the device refuses
        it with an illegal-data-address error, and None when no conclusion
        is possible (no client, transient failure, or ambiguous error
        response). Only False narrows the register map; None never does.
        """
        client = self._session.client
        if client is None:
            return None
        try:
            if kind == "discrete":
                result = await client.read_discrete_inputs(address, count)
            else:
                result = await client.read_input_registers(address, count)
        except ModbusInvalidAddressException:
            return False
        except _READ_EXCEPTIONS:
            return None
        if _is_error_result(self._session, result):
            # Response-object clients (demo mock, test fakes) surface
            # refusals as error responses; exception_code=2 is the
            # illegal-data-address refusal, anything else is ambiguous.
            if "exception_code=2" in str(result):
                return False
            return None
        return True

    async def detect_register_version(self) -> str | None:
        """Probe version-discriminating registers once and cache the outcome.

        Discrete input 26 exists on v2/v3 (MMI v2/v3, guide 1B/1C) but was
        dropped in v4 (MMI v4.x, guide 1D); input 138/139 only exist on v4.
        Each probe runs at most once per repository lifetime; transient
        failures stay uncached so a later call can retry them. The concluded
        version is logged once at INFO level; while unknown only a DEBUG
        line is emitted so unreachable devices do not spam the log.
        """
        if self._supports_discrete_26 is None:
            probed = await self._probe_register("discrete", 26, 1)
            if probed is not None:
                self._supports_discrete_26 = probed
                _LOGGER.debug(
                    "Discrete input 26 %s",
                    "present" if probed else "absent",
                )
        if self._supports_input_138_139 is None:
            probed = await self._probe_register("input", *_INPUT_V4_BATCH)
            if probed is not None:
                self._supports_input_138_139 = probed
                _LOGGER.debug(
                    "Input registers 138/139 %s",
                    "present" if probed else "absent",
                )
        version = self.register_version
        if version is not None:
            if version != self._last_logged_version:
                self._last_logged_version = version
                _LOGGER.info(
                    "Detected Daikin Modbus register map %s (%s)",
                    version,
                    _REGISTER_MAP_SOURCES[version],
                )
        else:
            _LOGGER.debug(
                "Modbus register map still unknown, using fallback "
                "(discrete 1-25, no version-specific registers)"
            )
        return version

    def _apply_signed_conversion(self, value: int, register_def) -> int:
        """Apply signed/unsigned conversion based on register data_type."""
        if (
            register_def is not None
            and hasattr(register_def, "data_type")
            and register_def.data_type is not None
            and register_def.data_type.signed
        ):
            return to_signed_16bit(value)
        return value

    def _apply_scaling(self, value: int, register_def) -> float:
        """Apply scaling based on register data_type."""
        if (
            register_def is not None
            and hasattr(register_def, "data_type")
            and register_def.data_type is not None
        ):
            return value * register_def.data_type.scaling
        return float(value)

    async def read_input_blocks(self) -> list[tuple[Any, int, int, int]]:
        """Read configured input-register blocks."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read input registers")
            return []

        blocks: list[tuple[Any, int, int, int]] = []

        # 🚀 OPTIMIZED: Single batch read for all input registers (21-87)
        # Before: 2 separate reads (21-53, 54-87)
        # After: 1 single read (21-87) = 50% faster!
        # Unit reads return flat lists and raise on failure; legacy clients
        # return response objects classified via _is_error_result.
        start_address, count = _INPUT_BATCH
        min_address, max_address, offset = 21, 87, 21
        try:
            block_start = time.time()
            result = await client.read_input_registers(
                start_address, count
            )  # 67 Register in einem Aufruf!
            _LOGGER.debug(
                "Optimized Input Register Block (21-87) read in %.3fs",
                time.time() - block_start,
            )

            if not _is_error_result(self._session, result):
                blocks.append((result, min_address, max_address, offset))
                _LOGGER.debug(
                    "✅ Batch optimization successful: 67 registers in 1 read"
                )
            else:
                _LOGGER.error("Optimized Input Register Block read failed")
        except ModbusInvalidAddressException as err:
            _LOGGER.warning(
                "Optimized Input Register Block not supported by device: %s", err
            )
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read optimized Input Register Block: %s", err)

        # v4-only input registers 138/139 (time until model restart +
        # active operation state): only polled once the probe proved them
        # present, so v2/v3 devices are never asked for absent registers.
        if self._supports_input_138_139 is True:
            v4_start, v4_count = _INPUT_V4_BATCH
            try:
                v4_start_time = time.time()
                v4_result = await client.read_input_registers(v4_start, v4_count)
                _LOGGER.debug(
                    "v4 Input Register Block (138-139) read in %.3fs",
                    time.time() - v4_start_time,
                )
                if not _is_error_result(self._session, v4_result):
                    blocks.append((v4_result, 138, 139, 138))
                else:
                    _LOGGER.warning("v4 Input Register Block (138-139) read failed")
            except ModbusInvalidAddressException as err:
                _LOGGER.warning(
                    "v4 Input Register Block (138-139) refused "
                    "(illegal data address), narrowing map: %s",
                    err,
                )
                self._supports_input_138_139 = False
            except _READ_EXCEPTIONS as err:
                _LOGGER.warning(
                    "Could not read v4 Input Register Block (138-139): %s", err
                )

        return blocks

    async def read_discrete_inputs(self) -> Any | None:
        """Read discrete inputs with one reconnect retry.

        The batch follows the detected register map: version-specific
        register 26 is only polled on the confirmed v2/v3 map; on v4 — and
        while the map is still unknown (fallback) — only 1-25 are polled.
        Should the full 1-26 batch ever be refused with an
        illegal-data-address error, the refusal itself narrows the map to v4
        and the read is retried as 1-25 without a reconnect (a reconnect
        could not make an absent register appear).
        """
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read discrete inputs")
            return None

        try:
            read_start = time.time()
            start_address, count = self._discrete_batch()
            result = await client.read_discrete_inputs(start_address, count)
            _LOGGER.debug(
                "Discrete Inputs (%s bits) read in %.3fs",
                count,
                time.time() - read_start,
            )

            if not _is_error_result(self._session, result):
                return result

            self._log_unsupported_register_type(result, "discrete inputs")
            return None
        except ModbusInvalidAddressException as err:
            if count > _DISCRETE_BATCH_V4[1]:
                _LOGGER.info(
                    "Discrete input batch 1-26 refused (illegal data address), "
                    "retrying as 1-25 for register map v4: %s",
                    err,
                )
                self._supports_discrete_26 = False
                return await self.read_discrete_inputs()
            _LOGGER.warning(
                "Device does not support discrete inputs (illegal data address): %s",
                err,
            )
            return None
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read Discrete Inputs: %s", err)
            return await self._retry_read_discrete_inputs()

    async def read_coils(self) -> Any | None:
        """Read coils with one reconnect retry."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read coils")
            return None

        try:
            read_start = time.time()
            start_address, count = _COILS_BATCH
            result = await client.read_coils(start_address, count)
            _LOGGER.debug("Coils (20 bits) read in %.3fs", time.time() - read_start)

            if not _is_error_result(self._session, result):
                return result

            self._log_unsupported_register_type(result, "coils")
            return None
        except ModbusInvalidAddressException as err:
            _LOGGER.warning(
                "Device does not support coils (illegal data address): %s", err
            )
            return None
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read Coils: %s", err)
            return await self._retry_read_coils()

    async def read_holding_blocks(self) -> list[tuple[Any, int, int, int]]:
        """Read configured holding-register blocks."""
        client = self._session.client
        if client is None:
            _LOGGER.error("Modbus client is None, cannot read holding registers")
            return []

        data_blocks: list[tuple[Any, int, int, int]] = []

        # v4 devices expose one extra holding register (81); the batch
        # grows to 1-81 only once input 138/139 proved the v4 map, so
        # v2/v3 devices are never asked for an absent register.
        start_address, count = self._holding_batch()
        end_address = start_address + count - 1
        try:
            block_start = time.time()
            result = await client.read_holding_registers(
                start_address, count
            )  # 80 (v2/v3) bzw. 81 (v4) Register in einem Aufruf!
            _LOGGER.debug(
                "Optimized Holding Register Block (1-%d) read in %.3fs",
                end_address,
                time.time() - block_start,
            )

            if not _is_error_result(self._session, result):
                data_blocks.append((result, 1, end_address, 1))
                if end_address == _HOLDING_BATCH_V4[0] + _HOLDING_BATCH_V4[1] - 1:
                    self._supports_holding_81 = True
                _LOGGER.debug(
                    "✅ Batch optimization successful: %d registers in 1 read",
                    count,
                )
            else:
                _LOGGER.warning(
                    "Device does not support full holding register range (1-%d)",
                    end_address,
                )
                # Fallback: Try individual blocks if full range fails
                await self._fallback_holding_blocks(data_blocks)
        except ModbusInvalidAddressException as err:
            if count > _HOLDING_BATCH[1] and self._supports_holding_81 is not False:
                _LOGGER.info(
                    "Holding register batch 1-%d refused (illegal data address), "
                    "register 81 is absent, retrying as 1-80: %s",
                    end_address,
                    err,
                )
                self._supports_holding_81 = False
                return await self.read_holding_blocks()
            _LOGGER.warning(
                "Device does not support full holding register range (1-%d): %s",
                end_address,
                err,
            )
            # Fallback: Try individual blocks on illegal address
            await self._fallback_holding_blocks(data_blocks)
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read optimized Holding Register Block: %s", err)
            # Fallback: Try individual blocks on error
            await self._fallback_holding_blocks(data_blocks)

        return data_blocks

    async def _fallback_holding_blocks(
        self, data_blocks: list[tuple[Any, int, int, int]]
    ) -> None:
        """Fallback to individual blocks if optimized batch fails."""
        blocks = [
            # (start, count, min, max, offset, name, optional); the last
            # block covers model-dependent registers and may legitimately
            # be absent.
            (
                start,
                count,
                start,
                start + count - 1,
                start,
                f"Block {index}",
                index == len(_HOLDING_FALLBACK_BLOCKS) - 1,
            )
            for index, (start, count) in enumerate(_HOLDING_FALLBACK_BLOCKS, start=1)
        ]
        _LOGGER.debug("Using fallback individual block reading")
        for start_addr, count, min_addr, max_addr, offset, name, optional in blocks:
            result = await self._read_holding_register_block(
                start_addr, count, min_addr, max_addr, offset, name, optional
            )
            if result is not None:
                data_blocks.append((result, min_addr, max_addr, offset))

        # v4-only register 81: only attempted once input 138/139 proved
        # the v4 map (and never after the main batch proved it refused),
        # so v2/v3 devices are never asked for an absent register. A miss
        # here only skips 81 for this cycle; the main-batch refusal path
        # above is what permanently narrows the map.
        if (
            self._supports_input_138_139 is True
            and self._supports_holding_81 is not False
        ):
            v4_start, v4_count = _HOLDING_V4_FALLBACK_BLOCK
            v4_result = await self._read_holding_register_block(
                v4_start, v4_count, v4_start, v4_start, v4_start, "Block v4", True
            )
            if v4_result is not None:
                data_blocks.append((v4_result, v4_start, v4_start, v4_start))
                self._supports_holding_81 = True

    async def read_raw_snapshot(
        self,
    ) -> tuple[dict[str, dict[int, int | bool]], dict[str, str]]:
        """Read all four spaces raw, keyed by 0-based unit address.

        Fresh reads in the spirit of the guide's ``async_read_raw``: raw
        undecoded values for the diagnostics download, directly
        ``load_raw``-compatible (Daikin address = raw address + 1).
        Failures are collected per space instead of raising, so one dead
        space never hides the others (UpdateReport-style failed map);
        partial holding data still merges with its error noted.
        """
        snapshot: dict[str, dict[int, int | bool]] = {
            "holding": {},
            "input": {},
            "coil": {},
            "discrete": {},
        }
        failed: dict[str, str] = {}
        client = self._session.client
        if client is None:
            return snapshot, {space: "no Modbus client available" for space in snapshot}

        def _record(space: str, err: Exception) -> None:
            failed.setdefault(space, f"{type(err).__name__}: {err}")

        start_address, count = _INPUT_BATCH
        try:
            result = await client.read_input_registers(start_address, count)
            snapshot["input"] = _raw_registers(result, start_address - 1)
        except Exception as err:
            _record("input", err)

        if self._supports_input_138_139:
            start_address, count = _INPUT_V4_BATCH
            try:
                result = await client.read_input_registers(start_address, count)
                snapshot["input"].update(_raw_registers(result, start_address - 1))
            except Exception as err:
                _record("input", err)

        start_address, count = self._holding_batch()
        try:
            result = await client.read_holding_registers(start_address, count)
            snapshot["holding"] = _raw_registers(result, start_address - 1)
        except Exception as err:
            _record("holding", err)
            chunks = list(_HOLDING_FALLBACK_BLOCKS)
            if self._supports_input_138_139 is True:
                chunks.append(_HOLDING_V4_FALLBACK_BLOCK)
            for chunk_start, chunk_count in chunks:
                try:
                    chunk = await client.read_holding_registers(
                        chunk_start, chunk_count
                    )
                    snapshot["holding"].update(_raw_registers(chunk, chunk_start - 1))
                except Exception as chunk_err:
                    _record("holding", chunk_err)

        start_address, count = self._discrete_batch()
        try:
            result = await client.read_discrete_inputs(start_address, count)
            snapshot["discrete"] = _raw_bits(result, start_address - 1)
        except Exception as err:
            _record("discrete", err)

        start_address, count = _COILS_BATCH
        try:
            result = await client.read_coils(start_address, count)
            snapshot["coil"] = _raw_bits(result, start_address - 1)
        except Exception as err:
            _record("coil", err)

        return snapshot, failed

    async def write_holding_register(self, register_name: str, value: int) -> Any:
        """Write a holding register by register name."""
        client = await self._session.ensure_connection()
        if client is None:
            error_msg = f"Cannot write holding register {register_name} - Modbus connection unavailable"
            _LOGGER.error(error_msg)
            raise ModbusConnectionException(error_msg)

        try:
            address = int(register_name.split("_")[1])
        except (ValueError, IndexError):
            error_msg = f"Invalid address name format: {register_name}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Validate and clamp address to valid Modbus range
        address = _validate_modbus_address(
            address, f"holding register address {register_name}"
        )

        register_config = get_register_config(register_name)

        # Convert signed value to unsigned for Modbus transmission if needed
        if (
            register_config is not None
            and hasattr(register_config, "data_type")
            and register_config.data_type is not None
            and register_config.data_type.signed
            and value < 0
        ):
            value = value + 65536  # Convert to 2's complement
            _LOGGER.debug(
                f"Converted signed value to unsigned for {register_name}: {value}"
            )

        try:
            result = await client.write_holding_register(address, value)
            if _is_error_result(self._session, result):
                error_msg = f"Failed to write register {register_name} (address {address}) with value {value}: {result}"
                _LOGGER.error(error_msg)
                raise ModbusDeviceException(error_msg)

            _LOGGER.debug(
                "Successfully wrote register %s (address %s) with value %s",
                register_name,
                address,
                value,
            )
            # Facade unit writes return None on success (no response object);
            # normalize to True so callers' `is not None` success checks keep
            # working on both the legacy and the unit path.
            return result if result is not None else True
        except _WRITE_EXCEPTIONS:
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as err:
            error_msg = f"Unexpected exception writing register {register_name} (address {address}) with value {value}: {err}"
            _LOGGER.error(error_msg)
            raise ModbusWriteException(error_msg) from err

    async def write_coil_register(self, register_name: str, value: bool) -> Any:
        """Write a coil register by register name."""
        client = await self._session.ensure_connection()
        if client is None:
            error_msg = (
                f"Cannot write coil {register_name} - Modbus connection unavailable"
            )
            _LOGGER.error(error_msg)
            raise ModbusConnectionException(error_msg)

        if isinstance(register_name, str) and register_name.startswith("coil_"):
            try:
                address = int(register_name.split("_")[1])
            except (ValueError, IndexError):
                error_msg = f"Invalid address name format: {register_name}"
                _LOGGER.error(error_msg)
                raise ValueError(error_msg)
        elif isinstance(register_name, int):
            address = register_name
        else:
            error_msg = f"Invalid address format: {register_name}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Validate and clamp address to valid Modbus range
        address = _validate_modbus_address(address, f"coil address {register_name}")

        try:
            result = await client.write_coil_register(address, value)
            if _is_error_result(self._session, result):
                error_msg = f"Failed to write coil {register_name} (address {address}) with value {value}: {result}"
                _LOGGER.error(error_msg)
                raise ModbusDeviceException(error_msg)

            _LOGGER.debug(
                "Successfully wrote coil %s (address %s) with value %s",
                register_name,
                address,
                value,
            )
            return result if result is not None else True
        except _WRITE_EXCEPTIONS:
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as err:
            error_msg = f"Unexpected exception writing coil {register_name} (address {address}) with value {value}: {err}"
            _LOGGER.error(error_msg)
            raise ModbusWriteException(error_msg) from err

    async def _retry_read_discrete_inputs(self) -> Any | None:
        """Reconnect and retry discrete inputs once."""
        try:
            _LOGGER.info(
                "Attempting to re-establish connection and retry discrete inputs"
            )
            client = await self._session.reconnect_with_new_client()
            if client is None:
                return None

            start_address, count = self._discrete_batch()
            result = await client.read_discrete_inputs(start_address, count)
            if not _is_error_result(self._session, result):
                _LOGGER.info("Successfully retried discrete inputs after reconnection")
                return result

            _LOGGER.warning(
                "Discrete inputs retry also failed - device may not support this register type: %s",
                result,
            )
            return None
        except ModbusInvalidAddressException as retry_err:
            _LOGGER.warning(
                "Discrete inputs retry refused (illegal data address): %s", retry_err
            )
            return None
        except _READ_EXCEPTIONS as retry_err:
            _LOGGER.warning("Retry attempt for discrete inputs failed: %s", retry_err)
            return None

    async def _retry_read_coils(self) -> Any | None:
        """Reconnect and retry coils once."""
        try:
            _LOGGER.info("Attempting to re-establish connection and retry coils")
            client = await self._session.reconnect_with_new_client()
            if client is None:
                return None

            start_address, count = _COILS_BATCH
            result = await client.read_coils(start_address, count)
            if not _is_error_result(self._session, result):
                _LOGGER.info("Successfully retried coils after reconnection")
                return result

            _LOGGER.warning(
                "Coils retry also failed - device may not support this register type: %s",
                result,
            )
            return None
        except ModbusInvalidAddressException as retry_err:
            _LOGGER.warning("Coils retry refused (illegal data address): %s", retry_err)
            return None
        except _READ_EXCEPTIONS as retry_err:
            _LOGGER.warning("Retry attempt for coils failed: %s", retry_err)
            return None

    async def _read_holding_register_block(
        self,
        start_address: int,
        count: int,
        min_address: int,
        max_address: int,
        offset: int,
        block_name: str,
        is_optional: bool,
    ) -> Any | None:
        """Read one holding-register block with reconnect retry."""
        client = self._session.client
        if client is None:
            return None

        try:
            block_start = time.time()
            result = await client.read_holding_registers(start_address, count)
            _LOGGER.debug(
                "Holding Register %s (%s registers) read in %.3fs",
                block_name,
                count,
                time.time() - block_start,
            )

            if not _is_error_result(self._session, result):
                return result

            if is_optional:
                _LOGGER.warning(
                    "Device does not support holding register %s (addresses %s-%s): %s",
                    block_name,
                    min_address,
                    max_address,
                    result,
                )
                _LOGGER.info(
                    "Skipping holding register %s - device may not support these address ranges",
                    block_name,
                )
            else:
                _LOGGER.error("Holding Register %s read failed: %s", block_name, result)
            return None
        except ModbusInvalidAddressException as err:
            _LOGGER.warning(
                "Device does not support holding register %s (addresses %s-%s): %s",
                block_name,
                min_address,
                max_address,
                err,
            )
            return None
        except _READ_EXCEPTIONS as err:
            _LOGGER.warning("Could not read Holding Register %s: %s", block_name, err)
            return await self._retry_holding_block(
                start_address,
                count,
                min_address,
                max_address,
                offset,
                block_name,
                is_optional,
            )

    async def _retry_holding_block(
        self,
        start_address: int,
        count: int,
        min_address: int,
        max_address: int,
        offset: int,
        block_name: str,
        is_optional: bool,
    ) -> Any | None:
        """Retry one holding block after reconnect."""
        del offset  # offset is part of repository contract, not needed for retry read

        try:
            _LOGGER.info(
                "Attempting to re-establish connection and retry holding register %s",
                block_name,
            )
            client = await self._session.reconnect_with_new_client()
            if client is None:
                return None

            retry_result = await client.read_holding_registers(start_address, count)
            if not _is_error_result(self._session, retry_result):
                _LOGGER.info(
                    "Successfully retried holding register %s after reconnection",
                    block_name,
                )
                return retry_result

            if is_optional:
                _LOGGER.warning(
                    "Holding Register %s retry also failed - device may not support these addresses: %s",
                    block_name,
                    retry_result,
                )
            else:
                _LOGGER.warning(
                    "Holding Register %s retry also failed: %s",
                    block_name,
                    retry_result,
                )
            return None
        except ModbusInvalidAddressException as retry_err:
            _LOGGER.warning(
                "Holding Register %s retry refused (illegal data address): %s",
                block_name,
                retry_err,
            )
            return None
        except _READ_EXCEPTIONS as retry_err:
            _LOGGER.warning(
                "Retry attempt for Holding Register %s failed: %s",
                block_name,
                retry_err,
            )
            return None

    @staticmethod
    def _log_unsupported_register_type(result: Any, register_type: str) -> None:
        """Log device support diagnostics for response-object clients.

        Response-object path only (demo mock, test fakes): pymodbus-style
        error responses carry ``exception_code`` details. Unit reads raise
        ``ModbusInvalidAddressException`` instead (handled at the call sites).
        """
        error_msg = str(result)
        if "exception_code=2" in error_msg:
            _LOGGER.warning(
                "Device does not support %s (Illegal data address)", register_type
            )
        elif "exception_code=1" in error_msg:
            _LOGGER.warning(
                "Device does not support %s (Illegal function)", register_type
            )
        else:
            _LOGGER.warning(
                "Device does not support %s or read failed: %s", register_type, result
            )
        _LOGGER.info(
            "Skipping %s - device may not support this register type", register_type
        )
