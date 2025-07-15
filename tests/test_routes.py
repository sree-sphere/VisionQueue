import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from services.storage import upload_image

# Mock upload_image() to avoid actual upload
client = TestClient(app)

# --- Fixtures for testing image upload endpoint ---

@pytest.fixture
def image_file():
    buf = io.BytesIO()
    buf.write(b"fake_image_content")
    buf.seek(0)
    return buf

@pytest.fixture
def metadata_json():
    return {
        "source": "unit-test",
        "filename": "test.jpg"
    }

# --- Tests for image upload endpoint ---

def test_upload_image_success(image_file, metadata_json):
    response = client.post(
        "/api/upload-image",
        files={"file": ("test.jpg", image_file, "image/jpeg")},
        data={"metadata": str(metadata_json), "callback_url": "https://webhook.site/test"}
    )
    assert response.status_code == 200
    assert "task_id" in response.json()

def test_upload_image_missing_file():
    # file is required -> FastAPI returns 422 if omitted
    response = client.post("/api/upload-image")
    assert response.status_code == 422  # default for missing fields

def test_upload_image_invalid_metadata():
    # send invalid JSON in metadata (missing closing brace, incomplete string)
    file_bytes = io.BytesIO(b"fake_image_data")
    response = client.post(
        "/api/upload-image",
        files={"file": ("test.jpg", file_bytes, "image/jpeg")},
        params={"metadata": '{"unclosed": "oops"'}  # malformed JSON
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid metadata JSON"

def test_upload_image_no_callback(image_file, metadata_json):
    response = client.post(
        "/api/upload-image",
        files={"file": ("test.jpg", image_file, "image/jpeg")},
        data={"metadata": str(metadata_json)}
    )
    assert response.status_code == 200
    assert "task_id" in response.json()

def test_upload_image_unsupported_format(image_file):
    response = client.post(
        "/api/upload-image",
        files={"file": ("bad.bmp", image_file, "image/bmp")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"

# --- Tests for error handling in image upload ---

@patch("api.routes.upload_image", side_effect=Exception("Simulated failure"))
def test_upload_image_storage_failure(mock_upload, client):
    file_data = io.BytesIO(b"dummy image bytes")
    response = client.post(
        "/api/upload-image",
        files={"file": ("test.jpg", file_data, "image/jpeg")},  # must be *.jpg
        data={"metadata": "{}", "callback_url": ""}
    )
    assert response.status_code == 500
    assert "Upload failed" in response.text

@patch("api.routes.submit_pipeline", return_value=None)
def test_pipeline_submission_returns_none(mock_submit, client):
    file_data = io.BytesIO(b"dummy image")
    response = client.post(
        "/api/upload-image",
        files={"file": ("test.jpg", file_data, "image/jpeg")}
    )
    assert response.status_code == 500
    assert "Pipeline submission failed" in response.text

class DummyResult:
    pass  # No .id

@patch("api.routes.submit_pipeline", return_value=DummyResult())
def test_pipeline_submission_missing_id(mock_submit, client):
    file_data = io.BytesIO(b"dummy image")
    response = client.post(
        "/api/upload-image",
        files={"file": ("test.jpg", file_data, "image/jpeg")}
    )
    assert response.status_code == 500
    assert "Pipeline submission failed" in response.text

# --- Tests for task status endpoint ---

def test_task_status_pending():
    with patch("services.celery_worker.celery_app.AsyncResult") as mock_res:
        mock_res.return_value.state = "PENDING"
        mock_res.return_value.result = None
        resp = client.get("/api/task-status/fake-task")
        assert resp.json()["state"] == "PENDING"

def test_task_status_failure():
    with patch("services.celery_worker.celery_app.AsyncResult") as mock_res:
        mock_res.return_value.state = "FAILURE"
        mock_res.return_value.result = "Something went wrong"
        resp = client.get("/api/task-status/fake-task")
        assert resp.json()["state"] == "FAILURE"
        assert "error" in resp.json()

def test_task_status_success():
    with patch("services.celery_worker.celery_app.AsyncResult") as mock_res:
        mock_res.return_value.state = "SUCCESS"
        mock_res.return_value.result = {"label": "cat"}
        resp = client.get("/api/task-status/fake-task")
        assert resp.json()["state"] == "SUCCESS"
        assert resp.json()["result"] == {"label": "cat"}

def test_task_status_running():
    with patch("services.celery_worker.celery_app.AsyncResult") as mock_res:
        mock_res.return_value.state = "STARTED"
        mock_res.return_value.result = None
        resp = client.get("/api/task-status/fake-task")
        assert resp.json()["state"] == "STARTED"
