"""Modbus protocol utilities for Daikin Altherma 4 integration."""

import logging

from ..const import SPECIAL_REGISTER_VALUES

_LOGGER = logging.getLogger(__name__)


class OneBasedModbusResponse:
    """Wrapper for Modbus responses to provide 1-based indexing."""

    def __init__(self, original_response, start_address: int, is_bits: bool = False):
        self.original_response = original_response
        self.start_address = start_address  # The starting address that was requested
        self.is_bits = is_bits
        # Track logged unavailable values to prevent spam
        self._logged_unavailable = set()
        # Cache for computed results to avoid repeated calculations
        self._registers_cache = None
        self._bits_cache = None

    @property
    def registers(self):
        """Return 1-based register array."""
        if self._registers_cache is not None:
            return self._registers_cache

        if hasattr(self.original_response, "registers"):
            # Size dynamically by requested start + returned payload length.
            payload_len = len(self.original_response.registers)
            max_possible_address = self.start_address + payload_len - 1
            result = [32766] * (max_possible_address + 1)

            # Place returned registers at the correct positions
            for i, value in enumerate(self.original_response.registers):
                result[self.start_address + i] = value
                # Log special Daikin MOdbus return values at debug level, only once per address
                # 32767: Register not supported
                # 32766: Register not available in current configuration
                # 32765: Waiting for value (not yet loaded)
                if value in SPECIAL_REGISTER_VALUES:
                    address_key = f"{value}_{self.start_address + i}"
                    if address_key not in self._logged_unavailable:
                        _LOGGER.debug(
                            "Modbus client returned special value %d at address %d",
                            value,
                            self.start_address + i,
                        )
                        self._logged_unavailable.add(address_key)

            return result
        else:
            self._registers_cache = [32766]  # Default with dummy element
            return self._registers_cache

    @property
    def bits(self):
        """Return 1-based bit array."""
        if self._bits_cache is not None:
            return self._bits_cache

        if hasattr(self.original_response, "bits"):
            # Size dynamically by requested start + returned payload length.
            payload_len = len(self.original_response.bits)
            max_possible_address = self.start_address + payload_len - 1
            result = [False] * (max_possible_address + 1)

            # Place returned bits at the correct positions
            for i, value in enumerate(self.original_response.bits):
                result[self.start_address + i] = value

            self._bits_cache = result
            return result
        else:
            self._bits_cache = [False]  # Default with dummy element
            return self._bits_cache

    def is_error(self):
        """Check if the original response is an error."""
        return (
            self.original_response.isError()
            if hasattr(self.original_response, "isError")
            else False
        )
