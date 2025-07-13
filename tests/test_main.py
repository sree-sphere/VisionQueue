import time
import main
from prometheus_client import Counter


def test_root(client):
    response = client.get("/")
    assert response.status_code == 404  # No root defined


def test_metrics_endpoint(client):
    # Register and increment a test metric
    c = Counter("dummy_metric_total", "Dummy metric for test")
    c.inc()

    # Short delay to allow metric file write (only needed in multiprocess mode)
    time.sleep(0.1)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "dummy_metric_total" in response.text


def test_metrics_endpoint_value_error_path(client, monkeypatch):
    """
    Simulates fallback to default REGISTRY if multiprocess setup fails.
    """

    def mock_multi_fail(registry):
        raise ValueError("Simulated multiprocess failure")

    monkeypatch.setattr("main.multiprocess.MultiProcessCollector", mock_multi_fail)

    response = client.get("/metrics")
    assert response.status_code == 200
    # Body should not be empty even when multiproc fails
    assert response.text.strip() != ""


def test_startup_event_runs_without_error():
    # Simply ensuring it does not raise any exceptions
    main.startup_event()
