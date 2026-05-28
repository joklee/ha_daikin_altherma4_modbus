"""Tests for translation key validation."""

import json
import re
from pathlib import Path

import pytest


def get_translation_keys_from_json(filepath: Path) -> set:
    """Extract all translation keys from a JSON translation file."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    keys = set()
    # Extract from entity section
    entity_section = data.get("entity", {})
    for platform, entities in entity_section.items():
        if isinstance(entities, dict):
            for key in entities.keys():
                keys.add(key)

    # Extract from device section (device translation keys)
    device_section = data.get("device", {})
    for key in device_section.keys():
        keys.add(key)

    return keys


def get_state_keys_from_json(filepath: Path) -> dict:
    """Extract all state keys per entity from a JSON translation file.

    Returns a dict of {entity_key: set_of_state_keys}.
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    state_keys = {}
    entity_section = data.get("entity", {})
    for platform, entities in entity_section.items():
        if isinstance(entities, dict):
            for entity_key, entity_value in entities.items():
                if isinstance(entity_value, dict) and "state" in entity_value:
                    full_key = f"{platform}.{entity_key}"
                    state_keys[full_key] = set(entity_value["state"].keys())

    return state_keys


def get_translation_keys_from_python(filepath: Path) -> set:
    """Extract all translation_key values from a Python file."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Match both formats:
    # - "translation_key": "value" (dict format in const.py)
    # - translation_key="value" (dataclass format in register_constants.py)
    pattern = r'["\']?translation_key["\']?\s*[:=]\s*["\']([^"\']+)["\']'
    return set(re.findall(pattern, content))


def extract_enum_map_values(filepath: Path) -> dict:
    """Extract enum_map values and their translation_keys from register_constants.py.

    Returns a dict of {translation_key: set_of_enum_values}.
    Handles both single-line and multi-line enum_map definitions.
    Skips complex dict comprehensions like {**{i: f"error_{i}" for i in range(100)}}.
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    result = {}
    # Find enum_map={...} blocks using balanced brace matching
    i = 0
    while i < len(content):
        marker = "enum_map={"
        idx = content.find(marker, i)
        if idx == -1:
            break

        start = idx + len(marker)
        # Find matching closing brace
        depth = 1
        j = start
        while j < len(content) and depth > 0:
            if content[j] == "{":
                depth += 1
            elif content[j] == "}":
                depth -= 1
            j += 1

        enum_content = content[start : j - 1]

        # Extract all string values from the enum_map
        values = set(re.findall(r'"([^"]+)"', enum_content))

        # Skip dict comprehensions with f-strings (e.g., "error_{i}")
        values = {v for v in values if "{" not in v and "}" not in v}

        if not values:
            i = j
            continue

        # Find the corresponding translation_key after this enum_map
        rest = content[j:]
        tk_match = re.search(r'translation_key="([^"]+)"', rest[:200])
        if tk_match:
            tk = tk_match.group(1)
            if tk in result:
                result[tk] |= values
            else:
                result[tk] = values

        i = j

    return result


class TestTranslations:
    """Test that all translation keys are properly defined."""

    @pytest.fixture
    def component_dir(self):
        """Return the path to the custom component directory."""
        return (
            Path(__file__).parent.parent
            / "custom_components"
            / "ha_daikin_altherma4_modbus"
        )

    @pytest.fixture
    def en_keys(self, component_dir):
        """Load all translation keys from en.json."""
        return get_translation_keys_from_json(
            component_dir / "translations" / "en.json"
        )

    @pytest.fixture
    def de_keys(self, component_dir):
        """Load all translation keys from de.json."""
        return get_translation_keys_from_json(
            component_dir / "translations" / "de.json"
        )

    @pytest.fixture
    def const_keys(self, component_dir):
        """Extract translation keys from const.py."""
        return get_translation_keys_from_python(component_dir / "const.py")

    @pytest.fixture
    def register_constants_keys(self, component_dir):
        """Extract translation keys from register_constants.py."""
        return get_translation_keys_from_python(component_dir / "register_constants.py")

    @pytest.fixture
    def all_python_keys(self, const_keys, register_constants_keys):
        """Return all translation keys from Python files."""
        return const_keys | register_constants_keys

    def test_all_python_keys_in_en_json(self, all_python_keys, en_keys):
        """Verify all translation keys from Python are in en.json."""
        missing = all_python_keys - en_keys
        assert not missing, f"Missing in en.json: {sorted(missing)}"

    def test_all_python_keys_in_de_json(self, all_python_keys, de_keys):
        """Verify all translation keys from Python are in de.json."""
        missing = all_python_keys - de_keys
        assert not missing, f"Missing in de.json: {sorted(missing)}"

    def test_no_orphaned_translations_in_en(self, en_keys, all_python_keys):
        """Warn about translations in en.json that don't exist in Python."""
        extra = en_keys - all_python_keys
        # These are expected extras (climate entities, calculated sensors, etc.)
        expected_extras = {
            "daikin_dhw_booster_thermostat",
            "daikin_dhw_manual_thermostat",
            "daikin_thermostat_climate",
            "external_electric_power",
            "input_29",  # orphaned translation
            "input_34",  # orphaned translation
            "input_53",
            "input_54",
            "input_55",
            "input_56",
            "input_57",
        }
        unexpected = extra - expected_extras
        assert not unexpected, (
            f"Orphaned translations in en.json (not in Python): {sorted(unexpected)}"
        )

    def test_no_orphaned_translations_in_de(self, de_keys, all_python_keys):
        """Warn about translations in de.json that don't exist in Python."""
        extra = de_keys - all_python_keys
        expected_extras = {
            "daikin_dhw_booster_thermostat",
            "daikin_dhw_manual_thermostat",
            "daikin_thermostat_climate",
            "external_electric_power",
            "input_29",  # orphaned translation
            "input_34",  # orphaned translation
            "input_53",
            "input_54",
            "input_55",
            "input_56",
            "input_57",
        }
        unexpected = extra - expected_extras
        assert not unexpected, (
            f"Orphaned translations in de.json (not in Python): {sorted(unexpected)}"
        )

    def test_translation_files_have_required_structure(self, component_dir):
        """Verify translation files have the required entity section."""
        for lang in ["en", "de"]:
            filepath = component_dir / "translations" / f"{lang}.json"
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            assert "entity" in data, f"Missing 'entity' section in {lang}.json"
            assert isinstance(data["entity"], dict), (
                f"'entity' must be a dict in {lang}.json"
            )

    def test_translation_consistency_between_languages(self, en_keys, de_keys):
        """Verify that en.json and de.json have the same translation keys."""
        allowed_diff = {"input_29", "input_34"}

        en_only = en_keys - de_keys - allowed_diff
        de_only = de_keys - en_keys - allowed_diff

        if en_only or de_only:
            msg = []
            if en_only:
                msg.append(f"Only in en.json: {sorted(en_only)}")
            if de_only:
                msg.append(f"Only in de.json: {sorted(de_only)}")
            pytest.fail("Translation keys mismatch:\n" + "\n".join(msg))

    def test_all_translations_have_name_field(self, component_dir):
        """Verify all translation entries have a 'name' field."""
        for lang in ["en", "de"]:
            filepath = component_dir / "translations" / f"{lang}.json"
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            entity_section = data.get("entity", {})
            missing_name = []

            for platform, entities in entity_section.items():
                if isinstance(entities, dict):
                    for key, value in entities.items():
                        if isinstance(value, dict) and "name" not in value:
                            missing_name.append(f"{platform}.{key}")

            assert not missing_name, (
                f"Missing 'name' field in {lang}.json: {sorted(missing_name)}"
            )

    def test_state_consistency_between_languages(self, component_dir):
        """Verify that state keys are consistent between en.json and de.json."""
        en_states = get_state_keys_from_json(component_dir / "translations" / "en.json")
        de_states = get_state_keys_from_json(component_dir / "translations" / "de.json")

        common_entities = set(en_states.keys()) & set(de_states.keys())

        mismatches = []
        for entity in sorted(common_entities):
            en_entity_states = en_states[entity]
            de_entity_states = de_states[entity]

            en_only = en_entity_states - de_entity_states
            de_only = de_entity_states - en_entity_states

            if en_only or de_only:
                msg_parts = [f"{entity}:"]
                if en_only:
                    msg_parts.append(f"  only in en: {sorted(en_only)}")
                if de_only:
                    msg_parts.append(f"  only in de: {sorted(de_only)}")
                mismatches.append("\n".join(msg_parts))

        assert not mismatches, (
            "State key mismatches between en.json and de.json:\n"
            + "\n\n".join(mismatches)
        )

    def test_all_state_keys_match_lowercase_pattern(self, component_dir):
        """Verify all state keys in translations match HA pattern [a-z0-9-_]+."""
        pattern = re.compile(r"^[a-z0-9_\-]+$")
        invalid = []

        for lang in ["en", "de"]:
            filepath = component_dir / "translations" / f"{lang}.json"
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            entity_section = data.get("entity", {})
            for platform, entities in entity_section.items():
                if isinstance(entities, dict):
                    for entity_key, entity_value in entities.items():
                        if isinstance(entity_value, dict) and "state" in entity_value:
                            for state_key in entity_value["state"]:
                                if not pattern.match(state_key):
                                    invalid.append(
                                        f"{lang}.json/{platform}.{entity_key} → "
                                        f"'{state_key}'"
                                    )

        assert not invalid, "State keys must match [a-z0-9-_]+:\n" + "\n".join(
            sorted(invalid)
        )

    def test_all_enum_map_values_translated_in_en_json(self, component_dir):
        """Verify all enum_map values have state translations in en.json."""
        rc_path = component_dir / "register_constants.py"
        enum_map = extract_enum_map_values(rc_path)
        en_states = get_state_keys_from_json(component_dir / "translations" / "en.json")

        missing = []
        for entity_key, values in sorted(enum_map.items()):
            en_entry = set()
            for full_key, state_keys in en_states.items():
                if full_key.endswith(f".{entity_key}"):
                    en_entry = state_keys
                    break

            missing_states = values - en_entry
            if missing_states and en_entry:
                missing.append(
                    f"{entity_key}: missing in en.json: {sorted(missing_states)}"
                )

        assert not missing, (
            "enum_map values missing as state keys in en.json:\n" + "\n".join(missing)
        )

    def test_all_enum_map_values_translated_in_de_json(self, component_dir):
        """Verify all enum_map values have state translations in de.json."""
        rc_path = component_dir / "register_constants.py"
        enum_map = extract_enum_map_values(rc_path)
        de_states = get_state_keys_from_json(component_dir / "translations" / "de.json")

        missing = []
        for entity_key, values in sorted(enum_map.items()):
            de_entry = set()
            for full_key, state_keys in de_states.items():
                if full_key.endswith(f".{entity_key}"):
                    de_entry = state_keys
                    break

            missing_states = values - de_entry
            if missing_states and de_entry:
                missing.append(
                    f"{entity_key}: missing in de.json: {sorted(missing_states)}"
                )

        assert not missing, (
            "enum_map values missing as state keys in de.json:\n" + "\n".join(missing)
        )
