import json
from pathlib import Path


def test_manifest_has_version():
    manifest_path = Path("custom_components/ha_daikin_altherma4_modbus/manifest.json")
    data = json.loads(manifest_path.read_text())

    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
