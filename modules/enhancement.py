"""
modules/enhancement.py
Image enhancement pipeline using OpenCV and scikit-image.
All functions accept a PIL Image and return a PIL Image.

Enhancement options:
    1. Remove blur     — sharpens blurry scans using unsharp masking
    2. Remove noise    — reduces random pixel variations using Non-local Means
    3. Remove artifacts — removes bright spots/rings using morphological ops
    4. Auto enhance    — CLAHE (Contrast Limited Adaptive Histogram Equalization)
"""

import cv2
import numpy as np
from PIL import Image
from skimage import restoration, filters
from skimage.morphology import disk


# ── Helpers ────────────────────────────────────────────────────

def pil_to_cv(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV numpy array (BGR)."""
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def cv_to_pil(img_array: np.ndarray) -> Image.Image:
    """Convert OpenCV numpy array (BGR) to PIL Image (RGB)."""
    return Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))


def to_grayscale_cv(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to grayscale OpenCV array."""
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)


# ── Enhancement functions ──────────────────────────────────────

def remove_blur(image: Image.Image) -> Image.Image:
    """
    Sharpens a blurry scan using Unsharp Masking.
    
    How it works:
    1. Create a blurred version of the image (Gaussian blur)
    2. Subtract the blur from the original — this gives you the "edges"
    3. Add those edges back to the original — result is sharper
    
    Good for: MRI scans that came out soft/blurry
    """
    img_cv = pil_to_cv(image)

    # create gaussian blur
    blurred = cv2.GaussianBlur(img_cv, (0, 0), sigmaX=3)

    # unsharp mask: original + (original - blurred) * strength
    sharpened = cv2.addWeighted(img_cv, 1.5, blurred, -0.5, 0)

    return cv_to_pil(sharpened)


def remove_noise(image: Image.Image) -> Image.Image:
    """
    Reduces noise using Non-local Means Denoising.
    
    How it works:
    Unlike simple blur (which makes everything soft), Non-local Means
    looks for similar patches across the entire image and averages them.
    This removes random noise while preserving important edges and details.
    
    Good for: grainy or speckled MRI scans
    """
    img_cv = pil_to_cv(image)

    # h controls denoising strength — higher = more denoising but more blurring
    # 10 is a good balance for medical images
    denoised = cv2.fastNlMeansDenoisingColored(
        img_cv,
        None,
        h=10,           # filter strength for luminance
        hColor=10,      # filter strength for color
        templateWindowSize=7,
        searchWindowSize=21
    )

    return cv_to_pil(denoised)


def remove_artifacts(image: Image.Image) -> Image.Image:
    """
    Removes artifacts (bright spots, rings, scanner noise) using
    morphological operations.
    
    How it works:
    - Opening (erosion then dilation) removes small bright spots
    - Closing (dilation then erosion) fills small dark holes
    - Works on grayscale then converts back to color
    
    Good for: DICOM scans with ring artifacts or bright noise spots
    """
    img_cv = pil_to_cv(image)
    gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # morphological opening — removes bright artifacts smaller than kernel
    kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    opened  = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

    # morphological closing — fills small dark holes
    closed  = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

    # blend with original to keep natural look
    result  = cv2.addWeighted(gray, 0.7, closed, 0.3, 0)

    # convert back to BGR then PIL
    result_bgr = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
    return cv_to_pil(result_bgr)


def auto_enhance(image: Image.Image) -> Image.Image:
    """
    Auto-enhances contrast using CLAHE
    (Contrast Limited Adaptive Histogram Equalization).
    
    How it works:
    Regular histogram equalization stretches contrast globally.
    CLAHE does it locally — divides image into small tiles and
    equalizes each tile separately. This brings out details in
    both bright and dark regions simultaneously.
    
    The "Contrast Limited" part prevents over-amplifying noise
    in flat regions (a common problem with regular equalization).
    
    Good for: low contrast scans where tumor regions are hard to see
    """
    img_cv = pil_to_cv(image)

    # work in LAB color space — CLAHE on L channel only
    # L = lightness, A/B = color — we only touch lightness
    lab    = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # apply CLAHE to lightness channel
    clahe  = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_eq   = clahe.apply(l)

    # merge back and convert to BGR
    lab_eq = cv2.merge([l_eq, a, b])
    result = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    return cv_to_pil(result)


# ── Main pipeline ──────────────────────────────────────────────

def apply_enhancements(
    image: Image.Image,
    remove_blur_flag: bool = False,
    remove_noise_flag: bool = False,
    remove_artifacts_flag: bool = False,
    auto_enhance_flag: bool = False,
) -> tuple[Image.Image, list[str]]:
    """
    Applies selected enhancements in sequence.
    Order matters — noise removal before sharpening gives better results.

    Args:
        image:                 Original PIL Image
        remove_blur_flag:      Apply blur removal
        remove_noise_flag:     Apply noise removal
        remove_artifacts_flag: Apply artifact removal
        auto_enhance_flag:     Apply CLAHE auto-enhancement

    Returns:
        (enhanced_image: PIL Image, applied: list of enhancement names)
    """
    enhanced = image.copy()
    applied  = []

    # order: artifacts → noise → blur → contrast
    # this order gives the best visual results

    if remove_artifacts_flag:
        enhanced = remove_artifacts(enhanced)
        applied.append("Artifact Removal")

    if remove_noise_flag:
        enhanced = remove_noise(enhanced)
        applied.append("Noise Removal")

    if remove_blur_flag:
        enhanced = remove_blur(enhanced)
        applied.append("Blur Removal")

    if auto_enhance_flag:
        enhanced = auto_enhance(enhanced)
        applied.append("Auto Enhancement (CLAHE)")

    return enhanced, applied
