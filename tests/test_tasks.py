import pytest
from unittest.mock import patch, MagicMock
from services import task_handler

# preprocess task
@patch("services.task_handler.preprocess_image", return_value=b"tensor-bytes")
def test_preprocess_success(mock_preprocess, dummy_image_bytes):
    """Test successful preprocessing returns tensor bytes."""
    result = task_handler.preprocess.run(dummy_image_bytes)
    assert result == b"tensor-bytes"
    mock_preprocess.assert_called_once()


@patch("services.task_handler.preprocess_image", side_effect=Exception("fail"))
def test_preprocess_failure(mock_preprocess, dummy_image_bytes):
    """Test preprocess raises exception on failure."""
    with pytest.raises(Exception):
        task_handler.preprocess.run(dummy_image_bytes)


# classify_task

@patch("services.task_handler.classify", return_value=[("class1", 0.9)])
def test_classify_success(mock_classify):
    """Test classify task returns expected list."""
    result = task_handler.classify_task.run(b"tensor-bytes")
    assert isinstance(result, list)
    assert len(result) > 0
    mock_classify.assert_called_once()


@patch("services.task_handler.classify", side_effect=Exception("fail"))
def test_classify_failure(mock_classify):
    """Test classify task raises exception on failure."""
    with pytest.raises(Exception):
        task_handler.classify_task.run(b"tensor-bytes")


# store_result

@patch("sqlalchemy.create_engine")
def test_store_result_success(mock_engine, dummy_result, dummy_metadata):
    """Test storing result inserts record and returns payload."""
    mock_conn = MagicMock()
    mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn

    result = task_handler.store_result.run(dummy_result, dummy_metadata)

    assert result["classification"] == dummy_result
    assert result["metadata"] == dummy_metadata
    assert "task_id" in result
    assert mock_conn.execute.called


@patch("sqlalchemy.create_engine", side_effect=Exception("db error"))
def test_store_result_failure(mock_engine, dummy_result, dummy_metadata):
    """Test store_result raises exception on DB failure."""
    with pytest.raises(Exception):
        task_handler.store_result.run(dummy_result, dummy_metadata)


# send_webhook

@patch("services.task_handler.requests.post")
def test_send_webhook_success(mock_post, dummy_result):
    """Test webhook sends POST and returns result."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = MagicMock()

    result = task_handler.send_webhook.run(dummy_result, "https://example.com/callback")

    assert result == dummy_result
    mock_post.assert_called_once()


@patch("services.task_handler.requests.post", side_effect=Exception("timeout"))
def test_send_webhook_failure(mock_post, dummy_result):
    """Test webhook raises exception on HTTP failure."""
    with pytest.raises(Exception):
        task_handler.send_webhook.run(dummy_result, "https://example.com/callback")


# submit_pipeline

from celery import signature

@patch("services.task_handler.celery_app.control.inspect")
@patch("services.task_handler.send_webhook.s")
@patch("services.task_handler.store_result.s")
@patch("services.task_handler.classify_task.s")
@patch("services.task_handler.preprocess.s")
def test_submit_pipeline_with_webhook(
    mock_pre, mock_classify, mock_store, mock_webhook, mock_inspect,
    dummy_image_bytes, dummy_metadata
):
    """Test pipeline chaining with webhook step included."""
    mock_pre.return_value = signature("step1")
    mock_classify.return_value = signature("step2")
    mock_store.return_value = signature("step3")
    mock_webhook.return_value = signature("step4")
    mock_inspect.return_value = {"worker": ["task1"]}

    pipeline_result = task_handler.submit_pipeline(dummy_image_bytes, dummy_metadata, "https://callback")
    assert pipeline_result is not None
    assert hasattr(pipeline_result, "id")


@patch("services.task_handler.celery_app.control.inspect", side_effect=Exception("fail"))
@patch("services.task_handler.store_result.s")
@patch("services.task_handler.classify_task.s")
@patch("services.task_handler.preprocess.s")
def test_submit_pipeline_without_webhook(
    mock_pre, mock_classify, mock_store, mock_inspect,
    dummy_image_bytes, dummy_metadata
):
    """Test pipeline chaining without webhook step."""
    mock_pre.return_value = signature("step1")
    mock_classify.return_value = signature("step2")
    mock_store.return_value = signature("step3")

    pipeline_result = task_handler.submit_pipeline(dummy_image_bytes, dummy_metadata)
    assert pipeline_result is not None
    assert hasattr(pipeline_result, "id")
