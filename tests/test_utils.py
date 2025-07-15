import os
import io
import time
import pytest
from utils import config
from utils.logger import logger

# Fixture to capture loguru logs
@pytest.fixture
def log_capture():
    buf = io.StringIO()
    handler_id = logger.add(buf, level="DEBUG", format="{message}", enqueue=True)
    yield buf
    logger.remove(handler_id)

# --- Tests for log_env_var utility ---

def test_log_env_var_required_missing(log_capture):
    """Test that log_env_var raises error and logs message if required key is missing."""
    key = "MISSING_REQUIRED_KEY"
    os.environ.pop(key, None)

    val = config.log_env_var(key, required=True)
    time.sleep(0.1)  # Let logger flush

    log_output = log_capture.getvalue()
    assert val is None
    assert f"{key} is NOT set" in log_output

def test_log_env_var_optional_missing(log_capture):
    """Test that log_env_var logs message if optional key is missing."""
    key = "MISSING_OPTIONAL_KEY"
    os.environ.pop(key, None)

    val = config.log_env_var(key, required=False)
    time.sleep(0.1)

    log_output = log_capture.getvalue()
    assert val is None
    assert f"{key} is not set (optional)" in log_output

def test_log_env_var_present(log_capture):
    """Test that log_env_var returns value if key is present."""
    key = "EXISTING_KEY"
    os.environ[key] = "dummy_value"

    val = config.log_env_var(key)
    time.sleep(0.1)

    log_output = log_capture.getvalue()
    assert val == "dummy_value"
    assert f"{key}=dummy_value" in log_output

# Tests for logger output

def test_logger_stdout_capture():
    """Test logger emits to stdout-compatible stream."""
    log_output = io.StringIO()
    handler_id = logger.add(log_output, format="{message}", level="INFO")
    logger.info("Logger test message")
    time.sleep(0.1)
    logger.remove(handler_id)

    contents = log_output.getvalue()
    assert "Logger test message" in contents
