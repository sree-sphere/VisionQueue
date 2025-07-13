"""
Encapsulates image preprocessing and classification logic.
"""

import io
from PIL import Image
import torch
import torchvision.transforms as T
from torchvision import models
from utils.config import MODEL_NAME
from loguru import logger
import numpy as np

# Load model once
def get_model():
    try:
        model = getattr(models, MODEL_NAME)(pretrained=True)
        model.eval()
        return model
    except AttributeError as e:
        logger.error(f"Model {MODEL_NAME} not found in torchvision.models")
        raise e

MODEL = get_model()
TRANSFORM = T.Compose([
    T.Resize(256),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225])
])

# Load ImageNet class labels
LABELS = []
with open("imagenet_classes.txt", "r") as f:
    LABELS = [line.strip() for line in f.readlines()]

def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Transforms an image and returns serialized tensor as bytes.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = TRANSFORM(img).unsqueeze(0)  # batch dim
    return tensor.numpy().astype(np.float32).tobytes()

def classify(tensor_bytes: bytes):
    """
    Deserializes tensor from bytes and performs classification.
    """
    tensor = torch.frombuffer(tensor_bytes, dtype=torch.float32).reshape(1, 3, 224, 224)
    with torch.no_grad():
        outputs = MODEL(tensor)
        probs = torch.nn.functional.softmax(outputs[0], dim=0)
        top5 = probs.topk(5)
        results = [
            {"label": LABELS[idx], "probability": float(prob)}
            for idx, prob in zip(top5.indices, top5.values)
        ]
        logger.debug(f"Top-5 results: {results}")
        return results
