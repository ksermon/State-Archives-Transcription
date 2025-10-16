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


def extract_line_boxes(
    image_bytes: bytes,
    *,
    min_area: int = 2000,
    min_area_ratio: float = 3e-4,   # ~0.03% of page area
    suppress_rules: bool = True,    # remove long horizontal rules
) -> List[Dict[str, float]]:
    """
    Return approximate line bounding boxes (normalized 0..1), sorted top-to-bottom.
    Uses:
      1) adaptive morphology (dilation) → contours
      2) horizontal-projection fallback if contours are poor
    """
    image = _load_image_from_bytes(image_bytes)
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binarized = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = 255 - binarized  # text as white

    h, w = image.shape[:2]

    # Optional: remove long horizontal rules to avoid merging lines
    if suppress_rules:
        h_kernel_len = max(25, int(w * 0.08))
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
        rules = cv2.morphologyEx(inv, cv2.MORPH_OPEN, h_kernel, iterations=1)
        inv = cv2.subtract(inv, rules)

    # 1) Adaptive dilation to connect characters in a line
    kw = max(15, int(w * 0.02))
    kh = max(5,  int(h * 0.008))
    connect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
    dilated = cv2.dilate(inv, connect_kernel, iterations=1)

    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area_rel = int(min_area_ratio * w * h)
    area_thresh = max(int(min_area), min_area_rel)

    boxes: List[Dict[str, float]] = []
    for cnt in contours:
        x, y, ww, hh = cv2.boundingRect(cnt)
        if ww * hh < area_thresh:
            continue
        pad = int(0.02 * max(ww, hh))
        x0 = max(x - pad, 0)
        y0 = max(y - pad, 0)
        w0 = min(ww + 2 * pad, w - x0)
        h0 = min(hh + 2 * pad, h - y0)
        boxes.append({"x": x0 / w, "y": y0 / h,
                     "width": w0 / w, "height": h0 / h})

    boxes.sort(key=lambda b: (b["y"], b["x"]))

    # 2) Fallback via horizontal projection if morphology under-detects
    if len(boxes) < 3:
        proj = inv.sum(axis=1)  # sum of white pixels per row
        thresh = 0.2 * proj.max()
        bands = []
        in_band = False
        start = 0
        for i, v in enumerate(proj):
            if not in_band and v > thresh:
                in_band = True
                start = i
            elif in_band and v <= thresh:
                end = i
                if end - start > max(8, int(h * 0.008)):
                    bands.append((start, end))
                in_band = False
        if in_band:
            end = len(proj) - 1
            if end - start > max(8, int(h * 0.008)):
                bands.append((start, end))

        boxes = []
        for (y0, y1) in bands:
            band = inv[y0:y1, :]
            vproj = band.sum(axis=0)
            col_thresh = 0.15 * vproj.max()
            cols = np.where(vproj > col_thresh)[0]
            if cols.size == 0:
                continue
            x0 = int(cols[0])
            x1 = int(cols[-1])
            pad_x = int(0.01 * w)
            pad_y = int(0.003 * h)
            x0 = max(x0 - pad_x, 0)
            x1 = min(x1 + pad_x, w - 1)
            y0p = max(y0 - pad_y, 0)
            y1p = min(y1 + pad_y, h - 1)
            boxes.append(
                {
                    "x": x0 / w,
                    "y": y0p / h,
                    "width": (x1 - x0) / w,
                    "height": (y1p - y0p) / h,
                }
            )

        boxes.sort(key=lambda b: (b["y"], b["x"]))

    return boxes


def synthesize_line_boxes(line_count: int, *, margin: float = 0.04) -> List[Dict[str, float]]:
    """
    Create evenly spaced horizontal strips from top to bottom (normalized),
    used as a fallback so we always have a 1:1 mapping to transcription lines.
    """
    if line_count <= 0:
        return []
    top = margin
    bottom = 1.0 - margin
    avail = max(0.05, bottom - top)
    step = avail / line_count
    boxes = []
    for i in range(line_count):
        y0 = top + i * step
        boxes.append(
            {"x": 0.05, "y": y0, "width": 0.90, "height": step * 0.85})
    return boxes


def get_image_dimensions(image_bytes: bytes) -> Optional[Dict[str, int]]:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            return {"width": width, "height": height}
    except Exception:
        return None
