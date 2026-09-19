"""Daikin abnormality fault-code decoding (issue #79).

The heat pump reports the abnormality code (input_22) as a 16-bit decimal
whose two bytes are ASCII characters, e.g. 14152 -> "7H". Together with
the sub code (input_23) this yields the documented fault code, e.g.
"7H-19".

FAULT_CODE_DESCRIPTIONS maps known main codes to short, self-written
titles (not verbatim manual text). Extend it code by code from the
installer reference guide; unknown codes still decode, only the
description stays empty.
"""

# Register values that never encode a fault (not available / no error /
# waiting). Mirrors SPECIAL_REGISTER_VALUES without importing HA-bound
# modules, so this module stays dependency-free.
_SPECIAL_VALUES = frozenset({0, 32765, 32766, 32767})

# Seed table: main code -> short factual title. Verified codes only;
# extend from the installer reference guide (e.g. 4PEN820808-1).
FAULT_CODE_DESCRIPTIONS: dict[str, str] = {
    "7H": "Water flow malfunction",
}


def decode_fault_code(value: int | None) -> str | None:
    """Decode a 16-bit abnormality code into two ASCII characters.

    Args:
        value: Raw register value (e.g. 14152).

    Returns:
        Two-character code (e.g. "7H"), or None when the value encodes
        no fault (special values, out of range, non-printable bytes).
    """
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number in _SPECIAL_VALUES or not 0 <= number <= 0xFFFF:
        return None
    high_byte = (number >> 8) & 0xFF
    low_byte = number & 0xFF
    if not (32 <= high_byte <= 126 and 32 <= low_byte <= 126):
        return None
    return chr(high_byte) + chr(low_byte)


def format_fault_code(code_raw: int | None, sub_raw: int | None) -> str | None:
    """Combine decoded main code and sub code, e.g. "7H-19".

    Returns just the main code when the sub code is missing/invalid,
    and None when nothing decodable is present.
    """
    code = decode_fault_code(code_raw)
    if code is None:
        return None
    try:
        sub = int(sub_raw) if sub_raw is not None else None
    except (TypeError, ValueError):
        sub = None
    if sub is None or sub < 0:
        return code
    return f"{code}-{sub}"


def describe_fault_code(code: str | None) -> str | None:
    """Return the short title for a decoded main code, if known."""
    if code is None:
        return None
    return FAULT_CODE_DESCRIPTIONS.get(code)


def format_abnormality_label(code_raw: int | None, sub_raw: int | None) -> str:
    """Build the repair-issue label, e.g. "7H-19 (raw 14152/19)".

    Falls back to the raw code or "unknown" when nothing decodes, and
    appends the known short title when the main code is in the table.
    """
    decoded = format_fault_code(code_raw, sub_raw)
    if decoded is None:
        return str(code_raw) if code_raw is not None else "unknown"
    raw_code = str(code_raw) if code_raw is not None else "unknown"
    raw_sub = str(sub_raw) if sub_raw is not None else "?"
    title = describe_fault_code(decoded.split("-")[0])
    label = f"{decoded} - {title}" if title else decoded
    return f"{label} (raw {raw_code}/{raw_sub})"
