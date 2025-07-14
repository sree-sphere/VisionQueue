# tests/test_classifier.py
import pytest
from core import classifier
import numpy as np
import torch
from unittest import mock

# Sample RGB image bytes (1x1 px)
@pytest.fixture
def dummy_image_bytes():
    from PIL import Image
    import io
    img = Image.new("RGB", (224, 224), color=(255, 0, 0))  # type: ignore[arg-type]
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_preprocess_image_shape(dummy_image_bytes):
    tensor_bytes = classifier.preprocess_image(dummy_image_bytes)
    array = np.frombuffer(tensor_bytes, dtype=np.float32).reshape(1, 3, 224, 224)
    assert array.shape == (1, 3, 224, 224)

def test_classify_returns_top5_format(dummy_image_bytes):
    tensor_bytes = classifier.preprocess_image(dummy_image_bytes)

    # patch model forward and softmax to return deterministic values
    with mock.patch.object(classifier.MODEL, 'forward', return_value=torch.randn(1, 1000)), \
         mock.patch('torch.nn.functional.softmax', return_value=torch.linspace(0.001, 1.0, 1000)):
        results = classifier.classify(tensor_bytes)
    
    assert isinstance(results, list)
    assert len(results) == 5
    assert all("label" in r and "probability" in r for r in results)
