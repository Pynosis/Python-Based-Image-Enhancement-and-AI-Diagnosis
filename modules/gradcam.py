"""
modules/gradcam.py
Generates Grad-CAM (Gradient-weighted Class Activation Mapping) heatmaps.

What is Grad-CAM?
It answers the question: "WHERE in the image did the model look
to make this prediction?"

How it works:
1. Run the image through the model
2. For the predicted class, compute gradients with respect to
   the last convolutional layer's feature maps
3. Average those gradients — positive values = important regions
4. Overlay as a colored heatmap on the original image
   (red = high attention, blue = low attention)

For DenseNet121, the last conv layer is inside features.denseblock4
"""

import torch
import numpy as np
import cv2
from PIL import Image
from modules.ai_model import load_model, preprocess, CLASS_NAMES


def generate_gradcam(
    image: Image.Image,
    predicted_class_idx: int
) -> Image.Image:
    """
    Generates a Grad-CAM heatmap overlay for the given image.

    Args:
        image:               Original PIL Image (RGB)
        predicted_class_idx: Index of the predicted class (0-3)

    Returns:
        PIL Image — original scan with heatmap overlaid
    """
    model = load_model()
    model.eval()

    # ── Hook setup ─────────────────────────────────────────────
    # Hooks let us "intercept" values flowing through the network
    # without modifying the model itself

    gradients  = []
    activations = []

    def save_gradient(grad):
        gradients.append(grad)

    def forward_hook(module, input, output):
        activations.append(output)
        output.register_hook(save_gradient)

    # attach hook to last dense block
    target_layer = model.features.denseblock4
    hook = target_layer.register_forward_hook(forward_hook)

    # ── Forward pass ───────────────────────────────────────────
    if image.mode != "RGB":
        image = image.convert("RGB")

    tensor = preprocess(image).unsqueeze(0)
    tensor.requires_grad_(True)

    output = model(tensor)

    # ── Backward pass for target class ─────────────────────────
    model.zero_grad()
    class_score = output[0, predicted_class_idx]
    class_score.backward()

    # ── Compute Grad-CAM ───────────────────────────────────────
    hook.remove()  # clean up hook

    gradient   = gradients[0].detach().numpy()[0]   # shape: (C, H, W)
    activation = activations[0].detach().numpy()[0]  # shape: (C, H, W)

    # global average pooling of gradients
    weights = np.mean(gradient, axis=(1, 2))  # shape: (C,)

    # weighted sum of activation maps
    cam = np.zeros(activation.shape[1:], dtype=np.float32)
    for i, w in enumerate(weights):
        cam += w * activation[i]

    # ReLU — only keep positive activations
    cam = np.maximum(cam, 0)

    # normalize to 0-1
    if cam.max() > 0:
        cam = cam / cam.max()

    # resize to original image size
    img_width, img_height = image.size
    cam_resized = cv2.resize(cam, (img_width, img_height))

    # ── Create heatmap overlay ─────────────────────────────────
    # convert to colormap (JET: blue=low, green=mid, red=high)
    heatmap = cv2.applyColorMap(
        np.uint8(255 * cam_resized),
        cv2.COLORMAP_JET
    )
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

    # convert original image to numpy
    original_np = np.array(image)

    # overlay heatmap on original (40% heatmap, 60% original)
    overlay = cv2.addWeighted(original_np, 0.6, heatmap, 0.4, 0)

    return Image.fromarray(overlay)


def get_class_idx(predicted_class: str) -> int:
    """Returns the index of a class name."""
    return CLASS_NAMES.index(predicted_class)
