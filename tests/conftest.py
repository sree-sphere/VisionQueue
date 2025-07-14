import pytest
import pathlib
from fastapi.testclient import TestClient
import os
from main import app

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

@pytest.fixture(scope="session", autouse=True)
def set_prometheus_env():
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = "/tmp/metrics-multiproc"
    os.makedirs("/tmp/metrics-multiproc", exist_ok=True)

@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    # Point to top-level docker-compose.yml
    return [str(pathlib.Path(__file__).parent.parent / "docker-compose.yml")]
