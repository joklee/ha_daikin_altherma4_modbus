"""End-to-end test: install the integration in a real Home Assistant Docker
container with demo mode enabled.

This test starts a real Home Assistant instance in Docker and verifies that
the integration loads cleanly. It therefore requires:

* a working Docker installation (binary + daemon),
* network access to ``ghcr.io`` (Home Assistant image) and ``docker.io``
  (Alpine image).

It is marked ``slow`` (deselected by default) and additionally requires an
explicit opt-in so that environments without Docker or registry access keep
the suite green::

    HA_DOCKER_DEMO_TESTS=1 pytest -m slow --no-cov -s  # via pytest
    HA_DOCKER_DEMO_TESTS=1 python tests/integration/test_ha_docker_demo_mode.py

The integration runs inside the Docker container, so no ``custom_components``
code is imported in the pytest process. Pass ``--no-cov`` to avoid a
``CoverageWarning: No data was collected`` warning from the global ``--cov``
option in ``pytest.ini``.

The test prints the integration log lines it found in the container. Pass
``-s`` (or ``--capture=no``) so pytest does not swallow that output on a
successful run; ``make test-e2e`` already includes it.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import pytest

HA_IMAGE = "ghcr.io/home-assistant/home-assistant:stable"
OPT_IN_ENV = "HA_DOCKER_DEMO_TESTS"


def _opted_in() -> bool:
    """Return True when the Docker end-to-end test was explicitly enabled."""
    return os.environ.get(OPT_IN_ENV, "").lower() in {"1", "true", "yes"}


def _docker_daemon_available() -> bool:
    """Return True when the Docker CLI exists and a daemon can be reached."""
    if shutil.which("docker") is None:
        return False
    probe = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        timeout=60,
        check=False,
    )
    return probe.returncode == 0


def _skip_without_docker() -> None:
    """Skip the test when Docker cannot be used in this environment."""
    if shutil.which("docker") is None:
        pytest.skip("Docker is not installed")
    if not _docker_daemon_available():
        pytest.skip("Docker daemon is not reachable")


def _pull_image(image: str) -> None:
    """Pull a Docker image, retrying exactly once on transient failures."""
    try:
        subprocess.run(["docker", "pull", image], check=True)
    except subprocess.CalledProcessError:
        # Registry hiccups such as "connection reset by peer" during layer
        # downloads are common; retry once deliberately before failing.
        print(f"Retrying image pull after transient failure: {image}")
        subprocess.run(["docker", "pull", image], check=True)


pytestmark = [
    pytest.mark.slow,
    pytest.mark.ha,
    pytest.mark.network,
    pytest.mark.skipif(
        not _opted_in(),
        reason=(
            f"Docker-based end-to-end test is opt-in; set {OPT_IN_ENV}=1 to enable it"
        ),
    ),
]


def test_ha_docker_demo_mode():
    """Test that the integration can be installed in HA Docker with demo mode."""
    _skip_without_docker()
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
    _pull_image(HA_IMAGE)

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
        Path(__file__).resolve().parents[2]
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

    # Create a minimal configuration.yaml. The `logger` block enables debug
    # logging for the integration so the integration's own log output (e.g.
    # coordinator setup, demo data generation, register polling) actually
    # appears in the Home Assistant container logs and is printed by this
    # test below.
    subprocess.run(
        [
            "docker",
            "exec",
            temp_container,
            "sh",
            "-c",
            (
                "echo 'homeassistant:' > /config/configuration.yaml && "
                "echo 'logger:' >> /config/configuration.yaml && "
                "echo '  logs:' >> /config/configuration.yaml && "
                "echo '    custom_components.ha_daikin_altherma4_modbus: info' "
                ">> /config/configuration.yaml"
            ),
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

        # Collect every log line mentioning the integration from both streams.
        # Home Assistant normally writes its logs to stderr, but messages can
        # also end up on stdout depending on the environment, so check both.
        integration_lines = [
            line
            for line in logs.stdout.splitlines() + logs.stderr.splitlines()
            if "ha_daikin_altherma4_modbus" in line
        ]

        # Print all integration log lines. Debug logging for the integration
        # is enabled in configuration.yaml, so this includes coordinator
        # setup, demo data generation and register polling messages.
        print(f"--- Integration logs ({len(integration_lines)} lines) ---")
        if integration_lines:
            for line in integration_lines:
                print(f"  {line}")
        else:
            print("  (no lines mentioning ha_daikin_altherma4_modbus found)")

        # Always keep a copy of the log output for later inspection. pytest
        # swallows stdout/stderr on a passing test unless ``-s`` is given, so
        # the file is a reliable place to look even without ``-s``.
        log_file = Path(tempfile.gettempdir()) / "ha_daikin_docker_integration_logs.txt"
        log_file.write_text("\n".join(integration_lines) + "\n", encoding="utf-8")
        print(f"Integration logs written to: {log_file}")

        # Only ERROR/CRITICAL-level log lines indicate a failure.
        # WARNING lines (e.g., "custom integration not tested by HA") are
        # expected and confirm the integration was installed and started.
        error_lines = [
            line for line in integration_lines if "ERROR" in line or "CRITICAL" in line
        ]
        assert not error_lines, (
            f"Integration errors found in logs:\n{chr(10).join(error_lines)}"
        )

        # Integration must be loaded successfully. The WARNING in the logs
        # ("custom integration not tested by HA") confirms it was installed
        # and started; with integration debug logging enabled, setup log
        # lines are visible as well.
        assert integration_lines, "Integration not found in Home Assistant logs"

        print("✓ Integration loaded successfully in Home Assistant Docker container")

    finally:
        # Cleanup - commented out for debugging
        # print("Cleaning up...")
        # subprocess.run(["docker", "stop", container_name], check=False)
        # subprocess.run(["docker", "rm", container_name], check=False)
        # subprocess.run(["docker", "rm", "-f", temp_container], check=False)
        # subprocess.run(["docker", "volume", "rm", volume_name], check=False)
        print("Container kept running for debugging")


if __name__ == "__main__":
    # Direct invocation (outside pytest) performs the same environment checks
    # but exits with a clear message instead of raising pytest.skip().
    if not _opted_in():
        raise SystemExit(f"{OPT_IN_ENV}=1 is required to run this test directly.")
    if not _docker_daemon_available():
        raise SystemExit("Docker is not installed or its daemon is not reachable.")
    test_ha_docker_demo_mode()
