"""Test integration installation in Home Assistant Docker container with demo mode."""

import json
import subprocess
import time
import uuid
from pathlib import Path


def test_ha_docker_demo_mode():
    """Test that the integration can be installed in HA Docker with demo mode."""
    # Use a different port to avoid conflicts
    port = "8124"
    container_name = "ha_demo_test"
    volume_name = "ha_demo_test_config"
    temp_container = "ha_demo_test_setup"

    # Cleanup any existing container and volume
    print("Cleaning up any existing container...")
    subprocess.run(["docker", "stop", container_name], check=False)
    subprocess.run(["docker", "rm", container_name], check=False)
    subprocess.run(["docker", "rm", temp_container], check=False)
    subprocess.run(["docker", "volume", "rm", volume_name], check=False)

    # Pull HA Docker image
    print("Pulling Home Assistant Docker image...")
    subprocess.run(
        ["docker", "pull", "ghcr.io/home-assistant/home-assistant:stable"],
        check=True,
    )

    # Create a named volume for HA config (avoids SELinux bind mount issues)
    print("Creating config volume...")
    subprocess.run(["docker", "volume", "create", volume_name], check=True)

    # Use a temporary container to populate the volume via docker cp
    # (avoids SELinux bind mount issues entirely)
    print("Populating config volume...")
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            temp_container,
            "-v",
            f"{volume_name}:/config",
            "alpine",
            "sleep",
            "30",
        ],
        check=True,
    )

    integration_dir = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ha_daikin_altherma4_modbus"
    )

    # Create custom_components directory in the volume
    subprocess.run(
        [
            "docker",
            "exec",
            temp_container,
            "mkdir",
            "-p",
            "/config/custom_components",
        ],
        check=True,
    )

    # Copy integration files into the volume
    subprocess.run(
        [
            "docker",
            "cp",
            str(integration_dir),
            f"{temp_container}:/config/custom_components/",
        ],
        check=True,
    )

    # Create minimal configuration.yaml
    subprocess.run(
        [
            "docker",
            "exec",
            temp_container,
            "sh",
            "-c",
            "echo 'homeassistant:' > /config/configuration.yaml",
        ],
        check=True,
    )

    # Create .storage directory for config entries
    subprocess.run(
        [
            "docker",
            "exec",
            temp_container,
            "mkdir",
            "-p",
            "/config/.storage",
        ],
        check=True,
    )

    # Pre-configure the integration in demo mode via a config entry.
    # This makes HA automatically set up the integration with demo mode.
    config_entry = {
        "entry_id": uuid.uuid4().hex,
        "version": 1,
        "minor_version": 1,
        "domain": "ha_daikin_altherma4_modbus",
        "title": "Daikin Altherma 4 Demo",
        "data": {"host": "127.0.0.1", "port": 502},
        "options": {
            "scan_interval": 10,
            "slow_scan_interval": 600,
            "demo_mode": True,
        },
        "preferred_disable_wave_entities": False,
        "preferred_disable_polling": False,
        "source": "user",
        "unique_id": "127.0.0.1:502",
        "disabled_by": None,
        "created_at": "2026-08-19T00:00:00+00:00",
        "updated_at": "2026-08-19T00:00:00+00:00",
        "discovery_keys": {},
    }
    config_entries_data = {
        "version": 1,
        "minor_version": 1,
        "key": "core.config_entries",
        "data": {"entries": [config_entry]},
    }
    payload = json.dumps(config_entries_data)
    subprocess.run(
        [
            "docker",
            "exec",
            temp_container,
            "sh",
            "-c",
            f"echo '{payload}' > /config/.storage/core.config_entries",
        ],
        check=True,
    )

    # Remove the temporary container (files persist in the volume)
    subprocess.run(["docker", "rm", "-f", temp_container], check=True)

    # Start HA container
    print("Starting Home Assistant container...")
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-v",
            f"{volume_name}:/config",
            "-p",
            f"{port}:8123",
            "ghcr.io/home-assistant/home-assistant:stable",
        ],
        check=True,
    )

    try:
        # Wait for HA to start
        print("Waiting for Home Assistant to start...")
        time.sleep(60)  # HA needs time to start

        # Check if HA is running
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        status = result.stdout.strip()
        if status != "running":
            # Get container logs to see why it failed
            logs = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True,
                text=True,
                check=False,
            )
            print(f"Container status: {status}")
            print(f"Container logs:\n{logs.stdout}")
            if logs.stderr:
                print(f"Container stderr:\n{logs.stderr}")
            raise RuntimeError(f"Container not running: {status}")

        print("Home Assistant is running")

        # Check logs for integration loading
        print("Checking Home Assistant logs...")
        logs = subprocess.run(
            ["docker", "logs", container_name],
            capture_output=True,
            text=True,
            check=False,
        )

        # Print all log lines mentioning the integration from stderr
        stderr_lines = [
            line
            for line in logs.stderr.splitlines()
            if "ha_daikin_altherma4_modbus" in line
        ]
        for line in stderr_lines:
            print(f"  {line}")

        # Only ERROR-level log lines in stderr indicate a failure.
        # WARNING lines (e.g., "custom integration not tested by HA") are
        # expected and confirm the integration was installed and started.
        error_lines = [
            line for line in stderr_lines if "ERROR" in line or "CRITICAL" in line
        ]
        assert not error_lines, (
            f"Integration errors found in stderr:\n{chr(10).join(error_lines)}"
        )

        # Integration must be loaded successfully. The WARNING in stderr
        # ("custom integration not tested by HA") confirms it was installed
        # and started.
        assert stderr_lines or "ha_daikin_altherma4_modbus" in logs.stdout, (
            "Integration not found in Home Assistant logs"
        )

        print("✓ Integration loaded successfully in Home Assistant Docker container")

    finally:
        # Cleanup
        print("Cleaning up...")
        subprocess.run(["docker", "stop", container_name], check=False)
        subprocess.run(["docker", "rm", container_name], check=False)
        subprocess.run(["docker", "rm", "-f", temp_container], check=False)
        subprocess.run(["docker", "volume", "rm", volume_name], check=False)


if __name__ == "__main__":
    test_ha_docker_demo_mode()
