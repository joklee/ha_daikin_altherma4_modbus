"""Unit tests for Daikin abnormality fault-code decoding (issue #79)."""

from custom_components.ha_daikin_altherma4_modbus.core.fault_codes import (
    decode_fault_code,
    describe_fault_code,
    format_abnormality_label,
    format_fault_code,
    raw_sub_code,
)


def test_raw_sub_code_accepts_only_raw_values():
    """Mapped display strings must never parse as sub codes."""
    assert raw_sub_code(19) == 19
    assert raw_sub_code(0) == 0
    assert raw_sub_code("19") == 19
    assert raw_sub_code(" 19 ") == 19
    assert raw_sub_code(None) is None
    assert raw_sub_code(True) is None
    assert raw_sub_code(-1) is None
    assert raw_sub_code("error_19") is None
    assert raw_sub_code("no_error") is None
    assert raw_sub_code(19.0) == 19


def test_mapped_sub_code_never_leaks_into_format():
    """An enum-mapped sub value degrades to the main code only."""
    assert format_fault_code(14152, "error_19") == "7H"
    assert format_abnormality_label(14152, "error_19") == (
        "7H - Water flow problem (raw 14152/?)"
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


def test_decode_accepts_already_decoded_text():
    """A decoded "7H" passes through; other strings do not."""
    assert decode_fault_code("7H") == "7H"
    assert decode_fault_code(" 7H ") == "7H"
    assert decode_fault_code("14152") == "7H"
    assert decode_fault_code("7H-19") is None
    assert decode_fault_code("X") is None
    assert decode_fault_code("") is None


def test_format_accepts_decoded_main_code():
    """format works with raw integers and pre-decoded text alike."""
    assert format_fault_code("7H", 19) == "7H-19"
    assert format_abnormality_label("7H", 19).startswith("7H-19 - ")


def test_format_combines_code_and_sub():
    """Main + sub code combine; missing sub yields the main code only."""
    assert format_fault_code(14152, 19) == "7H-19"
    assert format_fault_code(14152, None) == "7H"
    assert format_fault_code(14152, -3) == "7H"
    assert format_fault_code(None, 19) is None
    assert format_fault_code(32767, 19) is None


def test_describe_known_and_unknown():
    """Full codes resolve specifically, main codes via family fallback."""
    assert (
        describe_fault_code("7H-19")
        == "Water flow requirement problem at tank heat-up request"
    )
    assert describe_fault_code("7H") == "Water flow problem"
    assert describe_fault_code("7H-99") == "Water flow problem"
    assert describe_fault_code("ZZ") is None
    assert describe_fault_code("ZZ-01") is None
    assert describe_fault_code(None) is None


def test_table_covers_documented_codes():
    """Every extracted code resolves; spot-check across families."""
    from custom_components.ha_daikin_altherma4_modbus.core.fault_codes import (
        FAULT_CODE_TITLES,
    )

    assert len(FAULT_CODE_TITLES) >= 190
    assert FAULT_CODE_TITLES["89-05"].startswith("Heat exchanger freeze-up")
    assert FAULT_CODE_TITLES["E1-00"] == "OU: PCB defect"
    assert FAULT_CODE_TITLES["U4-00"] == "Indoor/outdoor unit communication problem"
    assert describe_fault_code("U4-00") == FAULT_CODE_TITLES["U4-00"]


def test_label_for_repair_issue():
    """Repair labels carry decoded code, title and raw values."""
    assert (
        format_abnormality_label(14152, 19)
        == "7H-19 - Water flow requirement problem at tank heat-up request"
        " (raw 14152/19)"
    )
    assert format_abnormality_label(14152, None) == (
        "7H - Water flow problem (raw 14152/?)"
    )
    assert format_abnormality_label(None, None) == "unknown"
    assert format_abnormality_label(None, 19) == "unknown"
