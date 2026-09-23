"""Daikin abnormality fault-code decoding (issue #79).

The heat pump reports the abnormality code (input_22) as a 16-bit decimal
whose two bytes are ASCII characters, e.g. 14152 -> "7H". Together with
the sub code (input_23) this yields the documented fault code, e.g.
"7H-19".

FAULT_CODE_TITLES holds one short title per documented fault code from
the installer reference guide (4PEN820808-1, Daikin Altherma 4 H W);
FAULT_MAIN_TITLES is the per-family fallback for codes not listed
individually. Titles are short factual phrases, not manual excerpts.
"""

# Register values that never encode a fault (not available / no error /
# waiting). Mirrors SPECIAL_REGISTER_VALUES without importing HA-bound
# modules, so this module stays dependency-free.
_SPECIAL_VALUES = frozenset({0, 32765, 32766, 32767})


FAULT_CODE_TITLES: dict[str, str] = {
    "7H-04": "Water flow problem during domestic hot water production",
    "7H-05": "Flow abnormality during space heating operation",
    "7H-06": "Abnormal flow during cooling operation",
    "7H-09": "Abnormal flow during emitter defrost",
    "7H-10": "Abnormal flow during tank defrost",
    "7H-11": "Flow abnormality during 4-way valve in cooling",
    "7H-12": "Main zone pump blocked abnormality",
    "7H-13": "Main zone pump electrical fault abnormality",
    "7H-14": "Add. zone pump communication error",
    "7H-15": "Add. zone pump blocked abnormality",
    "7H-16": "Add. zone pump electrical fault abnormality",
    "7H-17": "Main zone pump communication error",
    "7H-18": "Water flow requirement problem at space cooling request",
    "7H-19": "Water flow requirement problem at tank heat-up request",
    "7H-20": "Water flow requirement problem on emitter hydraulic circuit",
    "7H-21": "Water flow requirement problem on tank hydraulic circuit",
    "7H-22": "Water flow requirement problem at space heating request",
    "80-03": "Entering water temperature thermistor main zone abnormality",
    "80-04": "Entering water temperature thermistor add. zone abnormality",
    "81-00": "Exit water temperature thermistor after BUH abnormality",
    "81-05": "Loose hanging tank thermistor",
    "81-06": "Entering water temperature thermistor abnormality (indoor unit)",
    "81-07": "Exit water temperature thermistor after tank valve abnormality",
    "81-10": "Mixed water thermistor abnormality (mixing kit)",
    "89-01": "Heat exchanger freeze-up protection activated during defrost operation",
    "89-02": "Interruption defrost due to low water volume",
    "89-03": "Interruption defrost due to low water volume",
    "89-04": "Interruption defrost during tank defrost",
    "89-05": "Heat exchanger freeze-up protection activated during cooling operation. (error)",
    "89-06": "Heat exchanger freeze-up protection activated during cooling operation (warning)",
    "89-09": "Heat exchanger freeze-up protection activated during 4-way valve in cooling",
    "89-10": "Heat exchanger freeze-up protection activated during 4-way valve in cooling",
    "8C-03": "Undercooling of the space cooling water circuit",
    "8C-04": "Undercooling of the main zone water circuit",
    "8H-00": "Overheating of the space heating water circuit",
    "8H-01": "Overheating of the main zone water circuit",
    "8H-02": "Overheating of the main zone water circuit thermostat",
    "8H-03": "Overheating of the space heating water circuit thermostat",
    "8H-09": "Backup heater stuck detection ongoing",
    "8H-10": "Overheating mixed water safety thermostat (mixing kit)",
    "8H-11": "Overheating/undercooling mixed water circuit (mixing kit)",
    "A0-02": "Indoor unit gas sensor detection",
    "AA-01": "Backup heater overheated or BUH power cable not connected",
    "AA-07": "Diverter valve is blocked",
    "AA-08": "Mixing valve is blocked",
    "AA-09": "Diverter valve is broken",
    "AA-10": "Mixing valve is broken",
    "AA-11": "Tank valve is blocked",
    "AA-12": "Bypass valve is blocked",
    "AA-13": "Tank valve is broken",
    "AA-14": "Bypass valve is broken",
    "AH-00": "Tank disinfection function not completed correctly",
    "AJ-03": "DHW long heat-up abnormality",
    "C0-00": "Flow sensor abnormality",
    "C0-14": "Indoor gas sensor malfunction",
    "C0-15": "Indoor gas sensor disconnected",
    "CJ-02": "Room thermistor abnormality",
    "E0-06": "Outdoor unit leakage detection error",
    "E1-00": "OU: PCB defect",
    "E2-01": "Leakage current detection error",
    "E2-06": "Leakage current detection error",
    "E3-00": "OU: Actuation high pressure switch (HPS)",
    "E3-19": "OU: Actuation high pressure switch (HPS)",
    "E4-00": "Abnormal suction pressure",
    "E5-00": "OU: Overheat of inverter compressor motor",
    "E7-01": "OU: Malfunction of outdoor unit fan motor",
    "E7-05": "OU: Malfunction of outdoor unit fan motor",
    "E7-61": "OU: Malfunction of outdoor unit fan motor",
    "E7-63": "OU: Malfunction of outdoor unit fan motor",
    "E9-01": "Malfunction of electronic expansion valve",
    "E9-02": "Electronic expansion valve error due to wetness",
    "E9-03": "Malfunction of electronic expansion valve",
    "EA-01": "4WV switching error",
    "EC-00": "Abnormal increase tank temperature",
    "F3-01": "OU: Malfunction of discharge pipe temperature",
    "F3-02": "OU: Malfunction of discharge pipe temperature",
    "F3-20": "OU: Malfunction of discharge pipe temperature",
    "F3-24": "OU: Malfunction of discharge pipe temperature",
    "H0-02": "Outdoor unit gas sensor malfunction",
    "H0-04": "Outdoor unit gas sensor disconnection",
    "H1-00": "External temperature thermistor abnormality",
    "H3-01": "OU: Malfunction of high pressure switch (HPS)",
    "H3-08": "OU: Malfunction of high pressure switch (HPS)",
    "H7-01": "OU: Malfunction of outdoor unit fan motor",
    "H7-31": "Fan motor operation hours",
    "H9-00": "OU: Malfunction of outdoor air thermistor",
    "H9-01": "OU: Malfunction of outdoor air thermistor",
    "HC-00": "Tank thermistor abnormality",
    "HC-01": "Upper tank thermistor abnormality",
    "HC-02": "Lower tank thermistor abnormality",
    "HJ-10": "Water pressure sensor abnormality",
    "J3-01": "Discharge pipe Thermistor Abnormality",
    "J3-47": "Discharge pipe Thermistor Abnormality",
    "J5-00": "Malfunction of suction pipe thermistor",
    "J5-23": "Malfunction of suction pipe thermistor",
    "J6-00": "OU: Malfunction of heat exchanger thermistor",
    "J6-31": "Inlet water temperature Thermistor abnormality",
    "J6-32": "Leaving water temperature thermistor Abnormality (outdoor unit)",
    "J6-36": "OU: Malfunction of injection thermistor",
    "J6-42": "OU: Malfunction of injection thermistor",
    "J8-00": "Malfunction of refrigerant liquid thermistor",
    "J9-23": "Heat pipe thermistor abnormality",
    "JA-01": "OU: Malfunction of high pressure sensor",
    "JC-01": "Evaporator pressure abnormality",
    "L1-01": "Malfunction of INV PCB",
    "L1-02": "Malfunction of INV PCB",
    "L1-03": "Malfunction of INV PCB",
    "L1-04": "Malfunction of INV PCB",
    "L1-05": "Malfunction of INV PCB",
    "L1-06": "Malfunction of INV PCB",
    "L1-27": "Malfunction of INV PCB",
    "L1-31": "Malfunction of INV PCB",
    "L1-54": "Malfunction of INV PCB",
    "L1-55": "Malfunction of INV PCB",
    "L3-00": "OU: Electrical box temperature rise problem",
    "L4-00": "OU: Malfunction of inverter radiating fin temperature rise",
    "L4-01": "OU: Malfunction of inverter radiating fin temperature rise",
    "L4-06": "OU: Malfunction of inverter radiating fin temperature rise",
    "L4-07": "OU: Malfunction of inverter radiating fin temperature rise",
    "L5-00": "OU: Inverter instantaneous overcurrent (DC)",
    "L8-00": "Malfunction triggered by a thermal protection in the inverter PCB",
    "L8-01": "Malfunction triggered by a thermal protection in the inverter PCB",
    "L8-02": "Malfunction triggered by a thermal protection in the inverter PCB",
    "L8-03": "Malfunction triggered by thermal protection in the inverter PCB",
    "L8-04": "Malfunction triggered by thermal protection in the inverter PCB",
    "L8-05": "Malfunction triggered by thermal protection in the inverter PCB",
    "L8-14": "Malfunction triggered by thermal protection in the inverter PCB",
    "L9-01": "Malfunction in transmission system of outdoor unit",
    "L9-02": "Malfunction in transmission system of outdoor unit",
    "L9-03": "Malfunction in transmission system of outdoor unit",
    "L9-13": "Malfunction in transmission system of outdoor unit",
    "LC-00": "Malfunction in communication system of outdoor unit",
    "LC-01": "Malfunction in communication system of outdoor unit",
    "LC-02": "Malfunction in transmission system of outdoor unit",
    "LC-03": "Malfunction in transmission system of outdoor unit",
    "LC-05": "Malfunction in transmission system of outdoor unit",
    "LC-33": "Malfunction in transmission system of outdoor unit",
    "LH-01": "Converter error",
    "P1-00": "Open-phase power supply imbalance",
    "P3-01": "Abnormal direct current",
    "P3-04": "Abnormal direct current",
    "P4-01": "Fin thermistor abnormality",
    "P4-02": "Fin thermistor abnormality",
    "P4-03": "Fin thermistor abnormality",
    "PJ-01": "Capacity setting mismatch",
    "PJ-04": "Inverter PCB mismatch",
    "PJ-09": "Fan 1 mismatch",
    "U0-04": "OU: Shortage of refrigerant",
    "U0-12": "Refrigerant cooling dew condensation error",
    "U0-13": "OU: Shortage of refrigerant",
    "U0-14": "OU: Shortage of refrigerant",
    "U0-23": "OU: Shortage of refrigerant",
    "U0-36": "Low refrigerant pressure",
    "U1-00": "Malfunction by reverse phase/open-phase",
    "U1-01": "Malfunction by reverse phase/open-phase",
    "U2-01": "Supply voltage error",
    "U2-02": "Supply voltage error",
    "U2-03": "Supply voltage error",
    "U2-04": "Supply voltage error",
    "U2-07": "Supply voltage error",
    "U2-31": "Supply voltage error",
    "U2-35": "Supply voltage error",
    "U2-36": "Supply voltage error",
    "U2-37": "Supply voltage error",
    "U2-42": "Supply voltage error",
    "U2-43": "Supply voltage error",
    "U2-44": "Supply voltage error",
    "U3-00": "Underfloor heating screed dryout function not completed correctly",
    "U4-00": "Indoor/outdoor unit communication problem",
    "U8-01": "Connection with LAN adapter lost",
    "U8-02": "Connection with room thermostat lost",
    "U8-03": "No connection with room thermostat",
    "U8-04": "Unknown USB device",
    "U8-06": "MMI/bizone kit communication problem",
    "U8-07": "P1P2 communication error",
    "U8-11": "Connection with the Wireless gateway lost",
    "U8-22": "Display PCB in bootloader",
    "U8-23": "Display PCB communication issue",
    "U8-24": "Display PCB in back port mode",
    "U8-25": "Display PCB in self-test mode",
    "U8-26": "Room thermostat software version compatibility error",
    "U8-27": "Connection with multistep backup heater PCB lost",
    "U8-28": "Invalid DB error",
    "U8-29": "EEPROM loaded with errors",
    "UA-05": "Indoor/outdoor combination abnormality",
    "UA-07": "Indoor/outdoor combination abnormality",
    "UA-09": "Indoor/outdoor combination abnormality",
    "UA-48": "Outdoor unit standby power connector connection error",
    "UF-02": "Reversed piping or bad communication wiring detection",
    "UH-17": "Indoor unit locked (R290)",
    "UH-18": "Outdoor unit locked (R290)",
    "UH-19": "Too many unlock attempts",
    "UJ-14": "AF communication error",
    "UJ-20": "AF warning",
    "UJ-26": "AF caution",
}


FAULT_MAIN_TITLES: dict[str, str] = {
    "7H": "Water flow problem",
    "80": "Entering water temperature thermistor problem",
    "81": "Water temperature thermistor problem",
    "89": "Heat exchanger freeze-up protection",
    "8C": "Water circuit undercooling",
    "8H": "Water circuit overheating",
    "A0": "Indoor unit gas sensor problem",
    "AA": "Backup heater or valve problem",
    "AH": "Tank disinfection problem",
    "AJ": "DHW heat-up abnormality",
    "C0": "Sensor abnormality",
    "CJ": "Room thermistor abnormality",
    "E0": "Outdoor unit leakage detection error",
    "E1": "Outdoor unit PCB defect",
    "E2": "Leakage current detection error",
    "E3": "High pressure switch actuation",
    "E4": "Abnormal suction pressure",
    "E5": "Compressor motor overheat",
    "E7": "Outdoor unit fan motor malfunction",
    "E9": "Electronic expansion valve malfunction",
    "EA": "4-way valve switching error",
    "EC": "Abnormal tank temperature increase",
    "F3": "Discharge pipe temperature malfunction",
    "H0": "Outdoor unit gas sensor problem",
    "H1": "External temperature thermistor abnormality",
    "H3": "High pressure switch malfunction",
    "H7": "Outdoor unit fan motor malfunction",
    "H9": "Outdoor air thermistor malfunction",
    "HC": "Tank thermistor abnormality",
    "HJ": "Water pressure sensor abnormality",
    "J3": "Discharge pipe thermistor abnormality",
    "J5": "Suction pipe thermistor malfunction",
    "J6": "Heat exchanger thermistor malfunction",
    "J8": "Refrigerant liquid thermistor malfunction",
    "J9": "Heat pipe thermistor abnormality",
    "JA": "High pressure sensor malfunction",
    "JC": "Evaporator pressure abnormality",
    "L1": "Inverter PCB malfunction",
    "L3": "Electrical box temperature rise problem",
    "L4": "Inverter fin temperature malfunction",
    "L5": "Inverter overcurrent",
    "L8": "Inverter thermal protection trip",
    "L9": "Outdoor unit transmission malfunction",
    "LC": "Communication system malfunction",
    "LH": "Converter error",
    "P1": "Power supply phase imbalance",
    "P3": "Abnormal direct current",
    "P4": "Fin thermistor abnormality",
    "PJ": "Capacity setting mismatch",
    "U0": "Refrigerant shortage",
    "U1": "Power supply phase error",
    "U2": "Supply voltage error",
    "U3": "Screed dryout function not completed",
    "U4": "Indoor/outdoor unit communication problem",
    "U8": "Peripheral communication problem",
    "UA": "Indoor/outdoor combination abnormality",
    "UF": "Reversed piping or wiring problem",
    "UH": "Unit locked",
    "UJ": "Active filter problem",
}


def decode_fault_code(value: int | str | None) -> str | None:
    """Decode a 16-bit abnormality code into two ASCII characters.

    Args:
        value: Raw register value (e.g. 14152) or an already-decoded
            two-character code (e.g. "7H", passed through when valid).

    Returns:
        Two-character code (e.g. "7H"), or None when the value encodes
        no fault (special values, out of range, non-printable bytes).
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 2 and all(32 <= ord(char) <= 126 for char in text):
            return text
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


def raw_sub_code(value: int | str | None) -> int | None:
    """Normalize a sub-code register value to a raw integer.

    The coordinator stores raw register values, but input_23 also has an
    enum map (0..99 -> "error_0"..) applied at the display entity. This
    helper accepts only raw numeric values and explicitly rejects already
    mapped display strings like "error_19", so a mapped value can never
    be mistaken for a sub code.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            return None
        return int(text)
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def format_fault_code(
    code_raw: int | str | None, sub_raw: int | str | None
) -> str | None:
    """Combine decoded main code and sub code, e.g. "7H-19".

    Returns just the main code when the sub code is missing/invalid,
    and None when nothing decodable is present.
    """
    code = decode_fault_code(code_raw)
    if code is None:
        return None
    sub = raw_sub_code(sub_raw)
    if sub is None:
        return code
    return f"{code}-{sub}"


def describe_fault_code(code: str | None) -> str | None:
    """Return the short title for a fault code, if known.

    Accepts a full code ("7H-19", exact match) or a main code ("7H",
    family fallback). Unknown codes return None.
    """
    if code is None:
        return None
    if code in FAULT_CODE_TITLES:
        return FAULT_CODE_TITLES[code]
    return FAULT_MAIN_TITLES.get(code.split("-")[0])


def format_abnormality_label(
    code_raw: int | str | None, sub_raw: int | str | None
) -> str:
    """Build the repair-issue label, e.g. "7H-19 (raw 14152/19)".

    Falls back to the raw code or "unknown" when nothing decodes, and
    appends the known short title when the code is in the table. The
    displayed raw values are the normalized register values, never
    enum-mapped display strings.
    """
    decoded = format_fault_code(code_raw, sub_raw)
    if decoded is None:
        return str(code_raw) if code_raw is not None else "unknown"
    raw_code = str(code_raw) if code_raw is not None else "unknown"
    sub = raw_sub_code(sub_raw)
    raw_sub = str(sub) if sub is not None else "?"
    title = describe_fault_code(decoded)
    label = f"{decoded} - {title}" if title else decoded
    return f"{label} (raw {raw_code}/{raw_sub})"
