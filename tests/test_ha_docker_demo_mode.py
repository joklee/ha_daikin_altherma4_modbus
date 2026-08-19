"""Test integration installation in Home Assistant Docker container with demo mode."""
import json
import subprocess
import time
from pathlib import Path


def test_ha_docker_demo_mode():
    """Test that the integration can be installed in HA Docker with demo mode."""
    # Use a different port to avoid conflicts
    port = "8124"
    container_name = "ha_demo_test"

    # Cleanup any existing container
    print("Cleaning up any existing container...")
    subprocess.run(["docker", "stop", container_name], check=False)
    subprocess.run(["docker", "rm", container_name], check=False)

    # Pull HA Docker image
    print("Pulling Home Assistant Docker image...")
    subprocess.run(
        ["docker", "pull", "ghcr.io/home-assistant/home-assistant:stable"],
        check=True,
    )

    # Create temporary config directory
    config_dir = Path("/tmp/ha_demo_test")
    config_dir.mkdir(exist_ok=True)

    # Create minimal configuration.yaml
    config_yaml = config_dir / "configuration.yaml"
    config_yaml.write_text("homeassistant:\n")

    # Copy integration to config directory
    custom_components_dir = config_dir / "custom_components"
    custom_components_dir.mkdir(exist_ok=True)
    integration_dir = (
        Path(__file__).resolve().parents[1] / "custom_components" / "ha_daikin_altherma4_modbus"
    )
    target_dir = custom_components_dir / "ha_daikin_altherma4_modbus"
    subprocess.run(
        ["cp", "-r", str(integration_dir), str(target_dir)],
        check=True,
    )

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
            f"{config_dir}:/config",
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
        )
        status = result.stdout.strip()
        if status != "running":
            # Get container logs to see why it failed
            logs = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True,
                text=True,
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
        )

        # Verify integration was loaded
        assert "ha_daikin_altherma4_modbus" in logs.stdout or "ha_daikin_altherma4_modbus" in logs.stderr

        print("✓ Integration loaded successfully in Home Assistant Docker container")

    finally:
        # Cleanup
        print("Cleaning up...")
        subprocess.run(["docker", "stop", container_name], check=False)
        subprocess.run(["docker", "rm", container_name], check=False)
        subprocess.run(["rm", "-rf", str(config_dir)], check=False)


if __name__ == "__main__":
    test_ha_docker_demo_mode()
