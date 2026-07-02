"""
modules/dicom_handler.py
Handles DICOM file reading, validation, and conversion to PIL Image.
DICOM files contain medical metadata tags we use to verify
the scan is actually a brain MRI before running AI diagnosis.
"""

import pydicom
import numpy as np
from PIL import Image
import io


def read_dicom(file_bytes: bytes) -> dict:
    """
    Reads a DICOM file from raw bytes.
    Returns a dict with the pixel array and key metadata tags.
    
    Args:
        file_bytes: raw bytes of the .dcm file
        
    Returns dict with:
        image:        PIL Image ready for display/inference
        modality:     e.g. 'MR' for MRI, 'CT' for CT scan
        body_part:    e.g. 'BRAIN', 'HEAD'
        is_mri:       True if modality is MR
        is_brain:     True if body part is BRAIN or HEAD
        metadata:     dict of useful DICOM tags
    """
    # read DICOM from bytes
    ds = pydicom.dcmread(io.BytesIO(file_bytes))

    # extract pixel array
    pixel_array = ds.pixel_array

    # normalize to 0-255 range
    pixel_array = pixel_array.astype(np.float32)
    pixel_array -= pixel_array.min()
    if pixel_array.max() > 0:
        pixel_array /= pixel_array.max()
    pixel_array = (pixel_array * 255).astype(np.uint8)

    # convert to PIL Image
    if len(pixel_array.shape) == 2:
        # grayscale DICOM — convert to RGB for model
        image = Image.fromarray(pixel_array, mode='L').convert('RGB')
    else:
        image = Image.fromarray(pixel_array)

    # extract metadata tags safely
    modality   = str(getattr(ds, 'Modality', 'UNKNOWN')).upper()
    body_part  = str(getattr(ds, 'BodyPartExamined', 'UNKNOWN')).upper()
    patient_id = str(getattr(ds, 'PatientID', 'UNKNOWN'))
    study_desc = str(getattr(ds, 'StudyDescription', ''))

    return {
        "image":      image,
        "modality":   modality,
        "body_part":  body_part,
        "is_mri":     modality == "MR",
        "is_brain":   any(term in body_part for term in ["BRAIN", "HEAD", "CRANIAL"]),
        "metadata": {
            "modality":    modality,
            "body_part":   body_part,
            "patient_id":  patient_id,
            "study_desc":  study_desc,
        }
    }


def convert_to_pil(file_bytes: bytes, file_format: str) -> Image.Image:
    """
    Converts any supported format (DICOM, PNG, JPG) to PIL Image.
    Single entry point for all image types.
    
    Args:
        file_bytes:  raw bytes of the uploaded file
        file_format: 'dicom', 'png', 'jpg', 'jpeg'
        
    Returns: PIL Image in RGB mode
    """
    if file_format == 'dicom':
        result = read_dicom(file_bytes)
        return result["image"]
    else:
        # PNG or JPG — just open directly
        image = Image.open(io.BytesIO(file_bytes))
        return image.convert("RGB")


def validate_dicom_for_brain_mri(file_bytes: bytes) -> tuple[bool, str]:
    """
    Validates a DICOM file is a brain MRI using metadata tags.
    Returns (is_valid: bool, message: str)
    """
    try:
        result = read_dicom(file_bytes)

        if not result["is_mri"]:
            return False, f"This DICOM file is not an MRI scan (Modality: {result['modality']}). Only MRI scans are accepted for diagnosis."

        if not result["is_brain"]:
            return False, f"This MRI scan is not of the brain (Body Part: {result['body_part']}). Only brain MRI scans are accepted."

        return True, "Valid brain MRI DICOM file."

    except Exception as e:
        return False, f"Could not read DICOM file: {str(e)}"
