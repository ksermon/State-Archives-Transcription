import io
from typing import List, Optional, Dict

import cv2
import numpy as np
from PIL import Image


def _load_image_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    """Decode image bytes into an OpenCV BGR image."""
    if not image_bytes:
        return None
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    if image_array.size == 0:
        return None
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image


def extract_line_boxes(image_bytes: bytes, *, min_area: int = 2000) -> List[Dict[str, float]]:
    """Return approximate bounding boxes (normalized) for lines of text.

    The detection is intentionally model-agnostic so the coordinates can be reused
    regardless of which transcription engine produced the text.
    """
    image = _load_image_from_bytes(image_bytes)
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Binarize using Otsu's method. Invert so that text is white on black.
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = 255 - thresh

    # Connect characters along a line.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 7))
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    height, width = image.shape[:2]
    boxes: List[Dict[str, float]] = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area:
            continue
        pad = int(0.02 * max(w, h))
        x = max(x - pad, 0)
        y = max(y - pad, 0)
        w = min(w + 2 * pad, width - x)
        h = min(h + 2 * pad, height - y)
        boxes.append(
            {
                "x": x / width,
                "y": y / height,
                "width": w / width,
                "height": h / height,
            }
        )

    boxes.sort(key=lambda b: (b["y"], b["x"]))
    return boxes


def get_image_dimensions(image_bytes: bytes) -> Optional[Dict[str, int]]:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            return {"width": width, "height": height}
    except Exception:
        return None
