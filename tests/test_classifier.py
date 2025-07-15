import pytest
from core import classifier
import numpy as np
import torch
from unittest import mock

# --- Custom pytest fixtures ---

# Sample RGB image bytes (224x224 px)
@pytest.fixture
def dummy_image_bytes():
    from PIL import Image
    import io
    img = Image.new("RGB", (224, 224), color=(255, 0, 0))  # type: ignore[arg-type]
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

# --- Tests for classifier module ---

def test_preprocess_image_shape(dummy_image_bytes):
    """Ensure preprocess_image returns a tensor with shape (1, 3, 224, 224)."""
    tensor_bytes = classifier.preprocess_image(dummy_image_bytes)
    array = np.frombuffer(tensor_bytes, dtype=np.float32).reshape(1, 3, 224, 224)
    assert array.shape == (1, 3, 224, 224)

def test_classify_returns_top5_format(dummy_image_bytes):
    """
    Ensure classify returns a list of dicts with 'label' and 'probability'.
    """
    tensor_bytes = classifier.preprocess_image(dummy_image_bytes)

    # Use real softmax, but mock only the model forward pass
    torch.manual_seed(42)
    mock_logits = torch.randn(1, 1000)  # random but deterministic for coverage
    with mock.patch.object(classifier.MODEL, 'forward', return_value=mock_logits):
        results = classifier.classify(tensor_bytes)
    
    assert isinstance(results, list)
    assert len(results) == 5
    assert all("label" in r and "probability" in r for r in results)

@mock.patch("core.classifier.getattr", side_effect=AttributeError("Model not found"))
@mock.patch("core.classifier.MODEL_NAME", new="nonexistent_model")
def test_get_model_invalid(mock_getattr):
    """
    Simulate an invalid model name to trigger AttributeError in get_model().
    """
    with pytest.raises(AttributeError, match="Model not found"):
        classifier.get_model()
