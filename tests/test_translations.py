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
    def strings_keys(self, component_dir):
        """Load all translation keys from strings.json."""
        return get_translation_keys_from_json(component_dir / "strings.json")

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
        # Just assert no unexpected orphans - if there are, list them
        assert not unexpected, (
            f"Orphaned translations in en.json (not in Python): {sorted(unexpected)}"
        )

    def test_no_orphaned_translations_in_de(self, de_keys, all_python_keys):
        """Warn about translations in de.json that don't exist in Python."""
        extra = de_keys - all_python_keys
        # These are expected extras
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

    def test_all_python_keys_in_strings_json(self, all_python_keys, strings_keys):
        """Verify all translation keys from Python are in strings.json."""
        missing = all_python_keys - strings_keys
        assert not missing, f"Missing in strings.json: {sorted(missing)}"

    def test_strings_and_en_json_consistency(self, strings_keys, en_keys):
        """Verify strings.json and en.json have consistent entity translation keys."""
        # strings.json is the source of truth for English translations
        # en.json should have the same entity/device keys
        only_in_strings = strings_keys - en_keys
        only_in_en = en_keys - strings_keys

        if only_in_strings or only_in_en:
            msg = []
            if only_in_strings:
                msg.append(f"Only in strings.json: {sorted(only_in_strings)}")
            if only_in_en:
                msg.append(f"Only in en.json: {sorted(only_in_en)}")
            pytest.fail(
                "Inconsistency between strings.json and en.json:\n" + "\n".join(msg)
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

        # Also check strings.json has required structure
        strings_path = component_dir / "strings.json"
        with open(strings_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "entity" in data, "Missing 'entity' section in strings.json"
        assert isinstance(data["entity"], dict), (
            "'entity' must be a dict in strings.json"
        )

    def test_translation_consistency_between_languages(self, en_keys, de_keys):
        """Verify that en.json and de.json have the same translation keys."""
        # These keys exist in en.json but are orphaned (not in Python code)
        # They're kept for reference but not required in de.json
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

        # Find entities that have states in both languages
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
