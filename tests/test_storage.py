import io
import os
import pytest
from unittest import mock
from minio.error import S3Error

import services.storage as storage
from services.storage import init_minio_client, upload_image

@pytest.fixture(autouse=True)
def clear_minio_env(monkeypatch, tmp_path):
    """
    Ensure MINIO_ENDPOINT comes from environment and
    point PROMETHEUS_MULTIPROC_DIR to a temp dir for other tests.
    """
    # Provide a default endpoint if none set
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path / "metrics"))
    return

@mock.patch("services.storage.MINIO_ENDPOINT", new=None)
def test_init_minio_client_value_error():
    with pytest.raises(ValueError, match="MINIO_ENDPOINT is not set or is None"):
        init_minio_client()

@mock.patch("services.storage.Minio")
def test_init_minio_client_success(mock_minio):
    """
    init_minio_client returns (client, host, port) when the bucket exists.
    """
    mock_client = mock.MagicMock()
    mock_client.list_buckets.return_value = []
    mock_client.bucket_exists.return_value = True
    mock_minio.return_value = mock_client

    client, host, port = init_minio_client()
    assert client is mock_client
    assert host == "localhost"
    assert isinstance(port, int)

@mock.patch("services.storage.Minio")
def test_init_minio_client_makes_bucket(mock_minio):
    """
    If bucket does not exist, init_minio_client should call make_bucket.
    """
    mock_client = mock.MagicMock()
    mock_client.list_buckets.return_value = []
    mock_client.bucket_exists.return_value = False
    mock_minio.return_value = mock_client

    client, host, port = init_minio_client()
    mock_client.make_bucket.assert_called_once_with(storage.MINIO_BUCKET)

@mock.patch("services.storage.get_minio_client")
def test_upload_image_success(mock_get_client):
    mock_client = mock.MagicMock()
    mock_get_client.return_value = (mock_client, "localhost", 9000)

    data = b"dummy image bytes"
    obj_name = "test.jpg"
    url = upload_image(data, obj_name)
    
    mock_client.put_object.assert_called_once()
    assert obj_name in url
    assert url.startswith("http://")


@mock.patch("services.storage.get_minio_client")
def test_upload_image_failure(mock_get_client):
    mock_client = mock.MagicMock()
    mock_client.put_object.side_effect = S3Error("Upload failed", "", "", "", "", "", "")
    mock_get_client.return_value = (mock_client, "localhost", 1)

    data = b"dummy image bytes"
    with pytest.raises(S3Error):
        upload_image(data, "fail.jpg")

