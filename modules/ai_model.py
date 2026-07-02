"""
modules/ai_model.py
Loads the pretrained DenseNet121 model and runs inference on brain MRI scans.
Model was trained on Kaggle brain tumor dataset with 4 classes.
Saved using torch.save(model.state_dict(), ...) so we rebuild architecture first.
"""

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import streamlit as st
import time

# ── Constants ──────────────────────────────────────────────────
MODEL_PATH   = "best_model (2).pth"
IMAGE_SIZE   = 224
CONFIDENCE_THRESHOLD = 70.0  # below this = human review required

# must match the exact order used during training
CLASS_NAMES  = ['glioma', 'meningioma', 'notumor', 'pituitary']

# display-friendly names for the UI
CLASS_DISPLAY = {
    'glioma':      'Glioma',
    'meningioma':  'Meningioma',
    'notumor':     'No Tumor Detected',
    'pituitary':   'Pituitary Tumor',
}

# ── Image preprocessing ────────────────────────────────────────
# Must match exactly what was used during training
preprocess = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],   # ImageNet mean
        std=[0.229, 0.224, 0.225]     # ImageNet std
    )
])


# ── Model builder ──────────────────────────────────────────────
def build_model() -> nn.Module:
    """
    Rebuilds the exact same architecture used during training.
    Must match the Colab notebook exactly.
    """
    model = models.densenet121(weights=None)  # no pretrained weights, we load our own

    # exact same classifier head as in training notebook
    model.classifier = nn.Sequential(
        nn.Linear(model.classifier.in_features, 512),
        nn.ReLU(),
        nn.Dropout(0.5),
        nn.Linear(512, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, 4)
    )
    return model


# ── Load model (cached so it only loads once per session) ──────
@st.cache_resource
def load_model() -> nn.Module:
    """
    Loads the trained weights into the model.
    @st.cache_resource means this runs once and stays in memory.
    Every page rerun reuses the same loaded model — no re-loading.
    """
    device = torch.device("cpu")  # CPU since no GPU on local machine
    model  = build_model()

    # map_location="cpu" handles models saved on GPU (Google Colab)
    state_dict = torch.load(MODEL_PATH, map_location=torch.device("cpu"))
    model.load_state_dict(state_dict)

    model.to(device)
    model.eval()  # set to evaluation mode — disables dropout

    return model


# ── Inference ──────────────────────────────────────────────────
def predict(image: Image.Image) -> dict:
    """
    Runs inference on a PIL Image and returns prediction results.

    Args:
        image: PIL Image (RGB) — already validated as brain MRI

    Returns dict with:
        predicted_class:      e.g. 'glioma'
        display_name:         e.g. 'Glioma'
        confidence:           e.g. 87.34 (percentage)
        all_probabilities:    {'glioma': 87.34, 'meningioma': 5.2, ...}
        requires_human_review: True if confidence < 70%
        inference_time_ms:    how long inference took
    """
    model = load_model()

    # convert to RGB (handles grayscale DICOM converted images)
    if image.mode != "RGB":
        image = image.convert("RGB")

    # preprocess
    tensor = preprocess(image).unsqueeze(0)  # add batch dimension

    # run inference and time it
    start_time = time.time()
    with torch.no_grad():  # no gradient calculation needed for inference
        outputs     = model(tensor)
        probabilities = torch.softmax(outputs, dim=1)[0]  # convert logits to probabilities
    inference_time = int((time.time() - start_time) * 1000)  # ms

    # convert to numpy for easier handling
    probs_np = probabilities.cpu().numpy()

    # build results
    predicted_idx   = int(np.argmax(probs_np))
    predicted_class = CLASS_NAMES[predicted_idx]
    confidence      = float(probs_np[predicted_idx]) * 100

    all_probabilities = {
        CLASS_NAMES[i]: round(float(probs_np[i]) * 100, 2)
        for i in range(len(CLASS_NAMES))
    }

    return {
        "predicted_class":      predicted_class,
        "display_name":         CLASS_DISPLAY[predicted_class],
        "confidence":           round(confidence, 2),
        "all_probabilities":    all_probabilities,
        "requires_human_review": confidence < CONFIDENCE_THRESHOLD,
        "inference_time_ms":    inference_time,
    }


def predict_from_numpy(img_array: np.ndarray) -> dict:
    """
    Convenience wrapper — accepts numpy array (from OpenCV)
    and converts to PIL before running predict().
    Useful for enhanced images that come out of OpenCV as numpy arrays.
    """
    # OpenCV uses BGR, PIL uses RGB — convert
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_array = img_array[:, :, ::-1]  # BGR to RGB

    image = Image.fromarray(img_array.astype(np.uint8))
    return predict(image)
