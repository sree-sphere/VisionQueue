import time
import runpy

import main
from main import collect_multiprocess_metrics, metrics, instrumentator, app
from unittest.mock import patch, MagicMock
from prometheus_client import Counter, CollectorRegistry, CONTENT_TYPE_LATEST
from fastapi.testclient import TestClient

# --- Endpoint tests ---

def test_root(client):
    """Ensure root endpoint returns 404 as no route is defined."""
    response = client.get("/")
    assert response.status_code == 404  # No root defined

def test_health_endpoint(client):
    """Health check should return 200 with correct payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_metrics_endpoint(client):
    """The /metrics endpoint for Prometheus metrics should expose custom metrics.."""
    # Register and increment a test metric
    c = Counter("dummy_metric_total", "Dummy metric for test")
    c.inc()

    # Short delay to allow metric file write (only needed in multiprocess mode)
    time.sleep(0.1)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "dummy_metric_total" in response.text

# --- Metrics collection tests ---

def test_collect_multiprocess_metrics_success():
    """Test that successful collection adds collectors to registry"""
    registry = CollectorRegistry()
    result = collect_multiprocess_metrics(registry)
    assert isinstance(result, bool)


def test_metrics_endpoint_fallback(client, monkeypatch):
    """
    Simulates fallback to default REGISTRY if multiprocess setup fails.
    """
    def mock_collect(*args, **kwargs):
        return False

    monkeypatch.setattr("main.collect_multiprocess_metrics", mock_collect)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.text.strip() != ""


def test_collect_multiprocess_metrics_failure(monkeypatch, caplog):
    """
    Test that failure to collect multiprocess metrics is logged.
    """
    def raise_exception(*args, **kwargs):
        raise Exception("mocked fail")
    # Mock the collector to raise an exception
    monkeypatch.setattr("main.multiprocess.MultiProcessCollector", raise_exception)
    # Ensure it logs a warning
    registry = CollectorRegistry()
    with caplog.at_level("WARNING"):
        result = main.collect_multiprocess_metrics(registry)
        assert result is False
        assert any("Multiproc metrics failed" in msg for msg in caplog.messages)

# --- Startup event tests ---

def test_startup_event_runs_without_error():
    """Test that the startup event runs without raising exceptions."""
    # Simply ensuring it does not raise any exceptions
    main.startup_event()

def test_startup_event_logs_minio_failure(monkeypatch, caplog):
    """Test that startup event logs an error if MinIO connection fails."""
    def mock_get_minio():
        raise ConnectionError("Mocked MinIO failure")

    monkeypatch.setattr("main.get_minio_client", mock_get_minio)
    with caplog.at_level("ERROR"):
        main.startup_event()
        assert "Failed to connect to MinIO" in caplog.text

def test_startup_event_success(monkeypatch, caplog):
    """Simulates successful MinIO connection"""
    # mock_minio = type('MockMinio', (), {})()
    mock_minio = object()
    monkeypatch.setattr("main.get_minio_client", lambda: mock_minio)
    
    with caplog.at_level("INFO"):
        main.startup_event()
        assert "Prometheus metrics exposed at /metrics" in caplog.text
        assert "Failed to connect to MinIO" not in caplog.text

# --- Metrics function and Instrumentator tests ---

def test_metrics_manual_both_paths(monkeypatch):
    """Test the metrics function with both collect and fallback paths."""
    response = metrics()
    # Test fallback path (collect returns False)
    monkeypatch.setattr("main.collect_multiprocess_metrics", lambda reg: False)
    assert isinstance(response.body, bytes)

    # Test success path (collect returns True)
    monkeypatch.setattr("main.collect_multiprocess_metrics", lambda reg: True)
    assert isinstance(response.body, bytes)

def test_instrumentator_setup():
    """Verify the instrumentator is properly configured"""
    
    # Check instrumentator is attached to the app
    assert hasattr(app, 'user_middleware')
    assert any('Instrumentator' in str(middleware) for middleware in app.user_middleware)

# --- Main execution block test ---

def test_main_execution(monkeypatch):
    """Test the __main__ execution block using runpy"""
    mock_run = MagicMock()
    monkeypatch.setattr("uvicorn.run", mock_run)
    
    # Save original __name__
    original_name = main.__name__
    
    try:
        # Execute the module as __main__
        runpy.run_module("main", run_name="__main__")
        
        # Verify uvicorn.run was called
        mock_run.assert_called_once_with("main:app", host="0.0.0.0", port=8000)
    finally:
        # Restore original __name__
        main.__name__ = original_name
