import pytest
from unittest import mock
from minio.error import S3Error

import services.storage as storage
from services.storage import init_minio_client, upload_image, get_minio_client

# --- Fixtures for testing ---
@pytest.fixture(autouse=True)
def clear_env(monkeypatch, tmp_path):
    """Reset environment variables required by MinIO before each test."""
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "access")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("MINIO_BUCKET", "test-bucket")
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path / "metrics"))

@pytest.fixture(autouse=True)
def reset_minio_globals():
    """Reset MinIO client state in globals before each test."""
    storage._client = None
    storage._host = None
    storage._port = None

# --- Tests for storage module ---

# init_minio_client()

@mock.patch("services.storage.MINIO_ENDPOINT", new=None)
def test_init_minio_client_no_endpoint():
    """Test that init_minio_client raises ValueError if MINIO_ENDPOINT is not set."""
    with pytest.raises(ValueError, match="MINIO_ENDPOINT is not set or is None"):
        init_minio_client()

@mock.patch("services.storage.MINIO_BUCKET", new=None)
def test_init_minio_client_no_bucket(monkeypatch):
    """Should raise error if MINIO_BUCKET is not set."""
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    with pytest.raises(ValueError, match="MINIO_BUCKET is not set or is None"):
        init_minio_client()

@mock.patch("services.storage.Minio")
def test_init_minio_client_bucket_creation_failure(mock_minio):
    """Simulate S3Error when bucket creation fails."""
    client = mock.MagicMock()
    client.bucket_exists.return_value = False
    client.make_bucket.side_effect = S3Error("Create failed", "", "", "", "", "", "")
    mock_minio.return_value = client

    with pytest.raises(S3Error, match="Create failed"):
        init_minio_client()

@mock.patch("services.storage.Minio")
def test_init_minio_client_bucket_exists_success(mock_minio):
    """Test that init_minio_client returns client, host, and port when bucket exists."""
    client = mock.MagicMock()
    client.bucket_exists.return_value = True
    mock_minio.return_value = client

    result = init_minio_client()
    assert result[0] is client
    assert isinstance(result[1], str)  # host
    assert isinstance(result[2], int)  # port


# get_minio_client()

def test_get_minio_client_populates_globals(monkeypatch):
    """Test that get_minio_client initializes and caches client, host, and port."""
    dummy_client = mock.MagicMock()
    monkeypatch.setattr("services.storage.init_minio_client", lambda: (dummy_client, "localhost", 9000))

    client, host, port = get_minio_client()
    assert client is dummy_client
    assert host == "localhost"
    assert port == 9000

    # Second call should return cached values without calling init_minio_client again
    
    client2, _, _ = get_minio_client()
    assert client2 is client

def test_get_minio_client_connection_error(monkeypatch):
    """Simulate ConnectionError during init_minio_client()."""
    monkeypatch.setattr("services.storage.init_minio_client", lambda: (_ for _ in ()).throw(ConnectionError("fail")))
    with pytest.raises(ConnectionError, match="fail"):
        get_minio_client()


# upload_image()

def test_upload_image_valid(monkeypatch):
    """Test successful upload; ensure correct URL returned."""
    dummy_client = mock.MagicMock()
    monkeypatch.setattr("services.storage.get_minio_client", lambda: (dummy_client, "host", 1234))
    monkeypatch.setattr("services.storage.MINIO_BUCKET", "test-bucket")

    image_data = b"fake-bytes"
    obj_name = "abc.jpg"

    url = upload_image(image_data, obj_name)

    dummy_client.put_object.assert_called_once()
    assert "abc.jpg" in url
    assert url.startswith("http://host:1234/test-bucket/")

def test_upload_image_invalid_bucket(monkeypatch):
    """Test upload_image with empty MINIO_BUCKET."""
    monkeypatch.setattr("services.storage.MINIO_BUCKET", "")
    with pytest.raises(ValueError, match="MINIO_BUCKET must be a non-empty string"):
        upload_image(b"bytes", "file.jpg")

def test_upload_image_put_failure(monkeypatch):
    """Simulate S3Error during put_object() if MinIO client fails to upload."""
    mock_client = mock.MagicMock()
    mock_client.put_object.side_effect = S3Error("Upload failed", "", "", "", "", "", "")
    monkeypatch.setattr("services.storage.get_minio_client", lambda: (mock_client, "host", 1234))
    monkeypatch.setattr("services.storage.MINIO_BUCKET", "test-bucket")

    with pytest.raises(S3Error, match="Upload failed"):
        upload_image(b"bytes", "file.jpg")
