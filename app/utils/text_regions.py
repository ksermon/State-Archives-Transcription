import io
from typing import Dict, List

try:
    import cv2 as cv  # type: ignore
except Exception:  # pragma: no cover - gracefully degrade if OpenCV is unavailable
    cv = None  # type: ignore

import numpy as np
from PIL import Image


def extract_text_regions(image_bytes: bytes) -> List[Dict[str, float]]:
    """Return normalized bounding boxes for prominent text regions.

    The boxes are normalized to the image width/height so the caller can
    overlay them regardless of the rendered size on the page.
    """

    if not image_bytes or cv is None:
        return []

    with Image.open(io.BytesIO(image_bytes)) as image:
        rgb_image = image.convert("RGB")
        np_image = np.array(rgb_image)

    gray = cv.cvtColor(np_image, cv.COLOR_RGB2GRAY)

    # Smooth noise and emphasise darker text on lighter backgrounds.
    blurred = cv.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv.threshold(blurred, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)

    # Invert so text areas are white to help dilation join characters.
    inverted = cv.bitwise_not(thresh)

    # Merge characters within the same line into single contours.
    line_kernel = cv.getStructuringElement(cv.MORPH_RECT, (60, 10))
    dilated = cv.dilate(inverted, line_kernel, iterations=2)

    contours, _ = cv.findContours(dilated, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    height, width = gray.shape
    min_area = 0.0005 * width * height
    max_area = 0.9 * width * height

    boxes: List[Dict[str, float]] = []
    for contour in contours:
        x, y, w, h = cv.boundingRect(contour)
        area = w * h
        if area < min_area or area > max_area:
            continue

        boxes.append(
            {
                "left": x / width,
                "top": y / height,
                "width": w / width,
                "height": h / height,
            }
        )

    boxes.sort(key=lambda box: (box["top"], box["left"]))
    return boxes
