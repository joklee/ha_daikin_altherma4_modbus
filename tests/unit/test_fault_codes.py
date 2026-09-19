"""Unit tests for Daikin abnormality fault-code decoding (issue #79)."""

from custom_components.ha_daikin_altherma4_modbus.core.fault_codes import (
    decode_fault_code,
    describe_fault_code,
    format_abnormality_label,
    format_fault_code,
)


def test_decode_issue_example():
    """14152 decodes to '7H' (the code from the issue report)."""
    assert decode_fault_code(14152) == "7H"


def test_decode_boundaries():
    """Printable range edges decode; specials and garbage do not."""
    assert decode_fault_code(0x2020) == "  "
    assert decode_fault_code(0x7E7E) == "~~"
    assert decode_fault_code(None) is None
    assert decode_fault_code(0) is None
    assert decode_fault_code(32765) is None
    assert decode_fault_code(32766) is None
    assert decode_fault_code(32767) is None
    assert decode_fault_code(-1) is None
    assert decode_fault_code(0x10000) is None
    assert decode_fault_code(0x0000) is None
    # Control characters are not valid fault codes.
    assert decode_fault_code(0x0748) is None
    assert decode_fault_code("not-a-number") is None


def test_format_combines_code_and_sub():
    """Main + sub code combine; missing sub yields the main code only."""
    assert format_fault_code(14152, 19) == "7H-19"
    assert format_fault_code(14152, None) == "7H"
    assert format_fault_code(14152, -3) == "7H"
    assert format_fault_code(None, 19) is None
    assert format_fault_code(32767, 19) is None


def test_describe_known_and_unknown():
    """Seed table titles known codes; unknown codes stay untitled."""
    assert describe_fault_code("7H") == "Water flow malfunction"
    assert describe_fault_code("ZZ") is None
    assert describe_fault_code(None) is None


def test_label_for_repair_issue():
    """Repair labels carry decoded code, title and raw values."""
    assert (
        format_abnormality_label(14152, 19)
        == "7H-19 - Water flow malfunction (raw 14152/19)"
    )
    assert format_abnormality_label(14152, None) == (
        "7H - Water flow malfunction (raw 14152/?)"
    )
    assert format_abnormality_label(None, None) == "unknown"
    assert format_abnormality_label(None, 19) == "unknown"
