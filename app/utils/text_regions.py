import io
from typing import List, Optional, Dict, Tuple

import cv2
import numpy as np
from PIL import Image


# =========================
# Basic image helpers
# =========================

def _load_image_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    """Decode image bytes into an OpenCV BGR image."""
    if not image_bytes:
        return None
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    if image_array.size == 0:
        return None
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image


def _binarize_inverted(img_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (gray, bw, inv) where:
      gray: grayscale
      bw: Otsu binary (text dark → 0)
      inv: inverted (text bright → 255)
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = 255 - bw
    return gray, bw, inv


def get_image_dimensions(image_bytes: bytes) -> Optional[Dict[str, int]]:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            return {"width": width, "height": height}
    except Exception:
        return None


# =========================
# Legacy morphology (kept for completeness)
# =========================

def extract_line_boxes(
    image_bytes: bytes,
    *,
    min_area: int = 2000,
    min_area_ratio: float = 3e-4,
    suppress_rules: bool = True,
) -> List[Dict[str, float]]:
    """Approximate line boxes via morphology with a fallback."""
    image = _load_image_from_bytes(image_bytes)
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binarized = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = 255 - binarized  # text as white

    h, w = image.shape[:2]

    if suppress_rules:
        h_kernel_len = max(25, int(w * 0.08))
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
        rules = cv2.morphologyEx(inv, cv2.MORPH_OPEN, h_kernel, iterations=1)
        inv = cv2.subtract(inv, rules)

    kw = max(15, int(w * 0.02))
    kh = max(5,  int(h * 0.008))
    connect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
    dilated = cv2.dilate(inv, connect_kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

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
        boxes.append({"x": x0 / w, "y": y0 / h, "width": w0 / w, "height": h0 / h})

    boxes.sort(key=lambda b: (b["y"], b["x"]))

    if len(boxes) < 3:
        proj = inv.sum(axis=1)
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


# =========================
# Column detection helpers
# =========================

def _guess_columns_by_aspect(width: int, height: int) -> int:
    """Use aspect ratio: very wide pages → 2 columns, otherwise 1."""
    if height <= 0 or width <= 0:
        return 1
    aspect = width / float(height)
    return 2 if aspect >= 1.30 else 1


def _optional_valley_split(inv: np.ndarray) -> Optional[float]:
    """If a strong whitespace valley exists around center, return split x (0..1)."""
    h, w = inv.shape[:2]
    vproj = inv.sum(axis=0).astype(np.float64)
    k = max(5, int(0.01 * w) | 1)
    vker = np.ones(k, dtype=np.float64) / k
    vsm = np.convolve(vproj, vker, mode="same")

    thresh = 0.08 * (vsm.max() if vsm.size else 1.0)
    valleys = np.where(vsm < thresh)[0]
    if valleys.size == 0:
        return None
    center = w / 2.0
    idx = valleys[np.argmin(np.abs(valleys - center))]
    if idx < int(0.08 * w) or idx > int(0.92 * w):
        return None
    return idx / float(w)


# =========================
# Words → Quantile bands → Per-band pixel refinement (accurate X & Y)
# =========================

def _find_word_boxes(inv: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect words by dilating characters horizontally (small vertical kernel)."""
    h, w = inv.shape[:2]
    kw = max(9, int(0.012 * w))
    kh = max(3, int(0.006 * h))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
    words_map = cv2.dilate(inv, kernel, iterations=1)

    contours, _ = cv2.findContours(words_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    page_area = w * h
    min_word_area = max(20, int(1e-5 * page_area))
    for cnt in contours:
        x, y, ww, hh = cv2.boundingRect(cnt)
        if ww * hh < min_word_area:
            continue
        boxes.append((x, y, x + ww, y + hh))

    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes


def _strictly_increasing_ints(vals: np.ndarray) -> np.ndarray:
    """Ensure each subsequent value is > previous by at least 1 px."""
    out = vals.astype(int).copy()
    for i in range(1, len(out)):
        if out[i] <= out[i - 1]:
            out[i] = out[i - 1] + 1
    return out


def _refine_band_y(inv: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> Tuple[int, int]:
    """Refine band vertical limits using horizontal projection inside [y0:y1, x0:x1]."""
    hproj = inv[y0:y1, x0:x1].sum(axis=1)
    if hproj.size == 0 or hproj.max() <= 0:
        return y0, y1
    thr = 0.15 * hproj.max()
    rows = np.where(hproj > thr)[0]
    if rows.size == 0:
        return y0, y1
    top = y0 + int(rows[0])
    bot = y0 + int(rows[-1] + 1)
    # Small guard padding
    pad = max(1, int(0.003 * inv.shape[0]))
    top = max(y0, top - pad)
    bot = min(y1, bot + pad)
    if bot <= top:
        bot = top + 1
    return top, bot


def _refine_band_x(inv: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> Tuple[int, int]:
    """Refine band horizontal limits using vertical projection inside [y0:y1, x0:x1]."""
    vproj = inv[y0:y1, x0:x1].sum(axis=0)
    if vproj.size == 0 or vproj.max() <= 0:
        return x0, x1
    thr = 0.12 * vproj.max()
    cols = np.where(vproj > thr)[0]
    if cols.size == 0:
        return x0, x1
    left = x0 + int(cols[0])
    right = x0 + int(cols[-1] + 1)
    # Small guard padding
    pad = max(1, int(0.008 * (x1 - x0)))
    left = max(x0, left - pad)
    right = min(x1, right + pad)
    if right <= left:
        right = left + 1
    return left, right


def _bands_from_words(word_boxes: List[Tuple[int, int, int, int]], h: int, n_lines: int) -> np.ndarray:
    """Compute non-overlapping y-bands via quantiles of word y-centers."""
    if not word_boxes:
        # even bands
        bands = np.linspace(0, h, num=n_lines + 1, endpoint=True)
        return _strictly_increasing_ints(bands)

    ycenters = np.array([0.5 * (b[1] + b[3]) for b in word_boxes], dtype=np.float64)
    if not np.isfinite(ycenters).any() or np.allclose(ycenters.min(), ycenters.max()):
        bands = np.linspace(0, h, num=n_lines + 1, endpoint=True)
    else:
        q = np.linspace(0.0, 1.0, num=n_lines + 1)
        bands = np.quantile(ycenters, q)
    bands = _strictly_increasing_ints(bands)
    bands[0] = max(0, bands[0])
    bands[-1] = min(h, bands[-1])
    return bands


def extract_line_boxes_aligned(
    image_bytes: bytes,
    line_count: int,
    *,
    prefer_aspect_columns: bool = True,
    allow_valley_fallback: bool = True,
    # fine-tuning knobs
    y_refine: bool = True,
    x_refine: bool = True,
) -> List[Dict[str, float]]:
    """
    Produce exactly `line_count` line boxes (normalized 0..1) using:
      1) aspect-first column guess (optional valley split),
      2) words → non-overlapping quantile bands (by y-centers),
      3) per-band pixel refinement: horizontal proj refines Y, vertical proj refines X.

    This keeps bands stable & non-overlapping, while fitting boxes tightly to real ink.
    """
    if not image_bytes or line_count <= 0:
        return []

    img = _load_image_from_bytes(image_bytes)
    if img is None:
        return []

    gray, bw, inv = _binarize_inverted(img)
    h, w = inv.shape[:2]

    # 1) Columns
    columns = _guess_columns_by_aspect(w, h) if prefer_aspect_columns else 1
    split_x_norm: Optional[float] = None
    if allow_valley_fallback and columns >= 2:
        split_x_norm = _optional_valley_split(inv) or 0.5

    # 2) Words (whole page), then split words by column
    words_all = _find_word_boxes(inv)
    if columns == 1:
        segments = [(0, w, words_all)]
    else:
        split_x = int((split_x_norm or 0.5) * w)
        left_words = [b for b in words_all if (b[0] + b[2]) // 2 < split_x]
        right_words = [b for b in words_all if (b[0] + b[2]) // 2 >= split_x]
        segments = [(0, split_x, left_words), (split_x, w, right_words)]

    # 3) Distribute line_count across segments by word energy (sum of heights)
    seg_energy = [float(sum((b[3] - b[1]) for b in s[2])) for s in segments]
    total = sum(seg_energy) or 1.0
    weights = [e / total for e in seg_energy]
    counts = [int(np.floor(wt * line_count)) for wt in weights]
    for i, (_, _, words) in enumerate(segments):
        if words and counts[i] == 0:
            counts[i] = 1
    diff = line_count - sum(counts)
    if diff != 0:
        rema = [wt * line_count - c for wt, c in zip(weights, counts)]
        order = np.argsort(rema)[::-1]
        if diff > 0:
            for i in order[:diff]:
                counts[i] += 1
        else:
            for i in np.argsort(rema):
                if diff == 0:
                    break
                if seg_energy[i] > 0 and counts[i] <= 1:
                    continue
                counts[i] -= 1
                diff += 1
    while sum(counts) < line_count:
        j = int(np.argmax(seg_energy))
        counts[j] += 1
    while sum(counts) > line_count and any(c > 0 for c in counts):
        j = int(np.argmin(seg_energy))
        if counts[j] > 0:
            counts[j] -= 1
        else:
            for k in range(len(counts)):
                if counts[k] > 1:
                    counts[k] -= 1
                    break

    # 4) Build boxes per segment:
    boxes_px: List[Tuple[int, int, int, int]] = []
    for (seg_x0, seg_x1, seg_words), nL in zip(segments, counts):
        if nL <= 0:
            continue

        # 4a) y-bands by quantiles of y-center (non-overlapping)
        bands = _bands_from_words(seg_words, h, nL)

        # 4b) For each band, refine Y via horizontal projection, then refine X via vertical projection
        for i in range(nL):
            y0_band = int(bands[i])
            y1_band = int(bands[i + 1])
            if y1_band <= y0_band:
                y1_band = y0_band + 1

            y0_ref, y1_ref = (y0_band, y1_band)
            if y_refine:
                y0_ref, y1_ref = _refine_band_y(inv, seg_x0, seg_x1, y0_band, y1_band)

            x0_ref, x1_ref = (seg_x0, seg_x1)
            if x_refine:
                x0_ref, x1_ref = _refine_band_x(inv, seg_x0, seg_x1, y0_ref, y1_ref)

            # Defensive: ensure at least 1px in both directions
            if x1_ref <= x0_ref:
                x1_ref = x0_ref + 1
            if y1_ref <= y0_ref:
                y1_ref = y0_ref + 1

            boxes_px.append((x0_ref, y0_ref, x1_ref, y1_ref))

    # 5) Reading order: left→right, then top→bottom
    boxes_px.sort(key=lambda b: ((b[0] + b[2]) * 0.5, b[1]))

    # 6) Enforce tiny non-overlap in Y (defensive nudge)
    boxes_px_sorted = sorted(boxes_px, key=lambda b: (b[1], b[0]))
    for i in range(1, len(boxes_px_sorted)):
        prev = list(boxes_px_sorted[i - 1])
        cur = list(boxes_px_sorted[i])
        if cur[1] < prev[3]:
            # nudge current top to just below previous bottom (1px gap)
            cur[1] = prev[3] + 1
            if cur[3] <= cur[1]:
                cur[3] = cur[1] + 1
            boxes_px_sorted[i] = tuple(cur)
    boxes_px = boxes_px_sorted

    # 7) Normalize
    boxes_norm: List[Dict[str, float]] = []
    for (x0, y0, x1, y1) in boxes_px:
        boxes_norm.append({
            "x": x0 / float(w),
            "y": y0 / float(h),
            "width": max(1, x1 - x0) / float(w),
            "height": max(1, y1 - y0) / float(h),
        })

    # 8) Exact count guard
    if len(boxes_norm) != line_count:
        if len(boxes_norm) > line_count:
            boxes_norm = boxes_norm[:line_count]
        else:
            last = boxes_norm[-1] if boxes_norm else {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.03}
            for _ in range(line_count - len(boxes_norm)):
                boxes_norm.append(dict(last))

    return boxes_norm


# =========================
# Simple synthesizer (kept)
# =========================

def synthesize_line_boxes(line_count: int, *, margin: float = 0.04) -> List[Dict[str, float]]:
    """Evenly spaced strips as a final fallback."""
    if line_count <= 0:
        return []
    top = margin
    bottom = 1.0 - margin
    avail = max(0.05, bottom - top)
    step = avail / line_count
    boxes = []
    for i in range(line_count):
        y0 = top + i * step
        boxes.append({"x": 0.05, "y": y0, "width": 0.90, "height": step * 0.85})
    return boxes
