import pytest
import pathlib
import logging
import os

from fastapi.testclient import TestClient
from main import app
from loguru import logger

# --- Standard pytest fixtures ---

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture
def dummy_image_bytes():
    return b"fake_image_bytes"

@pytest.fixture
def dummy_metadata():
    return {"source": "unit-test", "filename": "data/goldfish.jpg"}

@pytest.fixture
def dummy_result():
    return {"top5": [("goldfish", 0.99)]}

# --- Custom pytest fixtures for integration tests (Environment Setup) ---

@pytest.fixture(scope="session", autouse=True)
def set_prometheus_env():
    # Ensure Prometheus multiprocess metrics directory exists for tests
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = "/tmp/metrics-multiproc"
    os.makedirs("/tmp/metrics-multiproc", exist_ok=True)

@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    # Point to top-level docker-compose.yml
    return [str(pathlib.Path(__file__).parent.parent / "docker-compose.yml")]

# --- Loguru for logging integration ---

@pytest.fixture(autouse=True)
def loguru_to_std_logging(caplog):
    """
    Redirect loguru logs to Python stdlib logging so they show in pytest output.
    """
    class PropagateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    logger.remove()
    logger.add(PropagateHandler(), format="{message}")