import pytest
from fastapi.testclient import TestClient
from src.main import app
import subprocess
import os

client = TestClient(app)

def test_fastapi_health_endpoint():
    """
    Test that the FastAPI application can boot and serve the /health endpoint correctly.
    This verifies the basic Python environment and framework setup.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

# Optional test to verify docker-compose syntax
def test_docker_compose_config():
    """
    Test that docker-compose.yml is valid. 
    Uses 'docker-compose config' to validate syntax without needing the daemon.
    """
    # Note: If docker-compose isn't in PATH on the runner, this might skip or fail.
    # We will just verify it runs if docker-compose is available.
    try:
        result = subprocess.run(["docker-compose", "config", "-q"], capture_output=True, text=True)
        assert result.returncode == 0, f"docker-compose.yml is invalid: {result.stderr}"
    except FileNotFoundError:
        pytest.skip("docker-compose executable not found, skipping config validation.")
