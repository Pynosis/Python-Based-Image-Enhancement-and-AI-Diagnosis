"""
modules/brain_validator.py
Pre-filter that runs BEFORE DenseNet121 to check if the
uploaded image is plausibly a brain MRI scan.

This prevents the model from running on chest X-rays,
random photos, or completely wrong inputs — the model
would still output a class (it doesn't know what it
doesn't know), so we need this gate.

For DICOM: uses metadata tags (reliable)
For PNG/JPG: uses image characteristics (heuristic)
"""

import numpy as np
from PIL import Image


def validate_image_for_diagnosis(
    image: Image.Image,
    file_format: str,
    dicom_metadata: dict = None
) -> tuple[bool, str]:
    """
    Validates that an image is suitable for brain tumor diagnosis.

    Args:
        image:          PIL Image
        file_format:    'dicom', 'png', 'jpg', 'jpeg'
        dicom_metadata: dict from dicom_handler.read_dicom() — only for DICOM files

    Returns:
        (is_valid: bool, message: str)
    """

    # ── DICOM validation — use metadata tags (reliable) ────────
    if file_format == 'dicom' and dicom_metadata:
        modality  = dicom_metadata.get("modality", "")
        body_part = dicom_metadata.get("body_part", "")

        if modality != "MR":
            return False, f"This scan is not an MRI (detected: {modality}). Only MRI brain scans are accepted for AI diagnosis."

        brain_terms = ["BRAIN", "HEAD", "CRANIAL", "NEURO"]
        if not any(term in body_part for term in brain_terms):
            return False, f"This MRI does not appear to be a brain scan (body part: {body_part}). Only brain MRI scans are accepted."

        return True, "Valid brain MRI."

    # ── PNG/JPG validation — heuristic checks ──────────────────
    # We can't read metadata from PNG/JPG, so we check
    # image characteristics that brain MRIs typically have.

    img_array = np.array(image.convert("L"))  # convert to grayscale

    height, width = img_array.shape

    # check 1: image must be reasonably sized
    if height < 64 or width < 64:
        return False, "Image is too small. Please upload a proper MRI scan."

    # check 2: brain MRIs are typically roughly square
    aspect_ratio = max(height, width) / min(height, width)
    if aspect_ratio > 2.5:
        return False, "Image proportions don't match a typical brain MRI scan."

    # check 3: brain MRIs have a large dark background (black)
    # typically >30% of pixels are very dark
    dark_pixels = np.sum(img_array < 20)
    total_pixels = height * width
    dark_ratio = dark_pixels / total_pixels

    if dark_ratio < 0.15:
        return False, "This image does not appear to be a brain MRI scan. Brain MRI scans typically have a dark background."

    # check 4: image must have meaningful content (not all black)
    mean_brightness = np.mean(img_array)
    if mean_brightness < 5:
        return False, "Image appears to be empty or completely black."

    if mean_brightness > 240:
        return False, "Image appears to be completely white or overexposed."

    return True, "Image accepted for diagnosis."


def validate_file_format(filename: str) -> tuple[bool, str, str]:
    """
    Validates the uploaded file has an accepted format.
    Returns (is_valid, message, detected_format)
    """
    ext = filename.lower().split(".")[-1]

    accepted = {
        "dcm":  "dicom",
        "dicom": "dicom",
        "png":  "png",
        "jpg":  "jpg",
        "jpeg": "jpeg",
    }

    if ext not in accepted:
        return False, f"File format '.{ext}' is not supported. Please upload a DICOM (.dcm), PNG, or JPG file.", ""

    return True, "Valid format.", accepted[ext]
