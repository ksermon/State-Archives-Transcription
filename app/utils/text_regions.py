import io
from typing import List, Optional, Dict, Tuple

import cv2
import numpy as np
from PIL import Image


# -----------------------
# IO helpers
# -----------------------

def _load_image_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    if not image_bytes:
        return None
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    if arr.size == 0:
        return None
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def get_image_dimensions(image_bytes: bytes) -> Optional[Dict[str, int]]:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            return {"width": w, "height": h}
    except Exception:
        return None


# -----------------------
# Binarization
# -----------------------

def _best_inv(img: np.ndarray) -> np.ndarray:
    """Return inverted mask (text=255) chosen from Otsu/Adaptive by ink ratio."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Otsu
    _, bw_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv_otsu = 255 - bw_otsu

    # Adaptive
    block = max(21, (int(0.018 * max(img.shape[:2])) // 2) * 2 + 1)
    C = 10
    bw_adapt = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, C
    )
    inv_adapt = 255 - bw_adapt

    # Pick by ink ratio closest to ~20% within sane bounds
    cands = [inv_otsu, inv_adapt]
    target = 0.20
    best = cands[0]
    best_score = float("inf")
    for inv in cands:
        ratio = float(inv.mean()) / 255.0
        if 0.01 <= ratio <= 0.70:
            score = abs(ratio - target)
            if score < best_score:
                best_score = score
                best = inv
    return best


# -----------------------
# Column split helpers
# -----------------------

def _guess_columns_by_aspect(w: int, h: int) -> int:
    if w <= 0 or h <= 0:
        return 1
    return 2 if (w / float(h)) >= 1.30 else 1


def _center_valley(inv: np.ndarray) -> Optional[int]:
    """Return x split at central whitespace valley if present (for spreads/columns)."""
    h, w = inv.shape[:2]
    vproj = inv.sum(axis=0).astype(np.float64)
    if vproj.size == 0:
        return None
    k = max(5, int(0.01 * w) | 1)
    vsm = np.convolve(vproj, np.ones(k) / k, mode="same")
    thr = 0.08 * vsm.max()
    valleys = np.where(vsm < thr)[0]
    if valleys.size == 0:
        return None
    center = w / 2.0
    x = int(valleys[np.argmin(np.abs(valleys - center))])
    if x < int(0.08 * w) or x > int(0.92 * w):
        return None
    return x


# -----------------------
# Word detection
# -----------------------

def _remove_horizontal_rules(inv: np.ndarray) -> np.ndarray:
    h, w = inv.shape[:2]
    rule_len = max(25, int(w * 0.08))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (rule_len, 1))
    rules = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel, iterations=1)
    return cv2.subtract(inv, rules)


def _word_boxes(inv: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Return word-like boxes (x0,y0,x1,y1) using connected components with a
    light horizontal dilation to join letters within a word.
    """
    inv = _remove_horizontal_rules(inv)

    h, w = inv.shape[:2]
    kw = max(7, int(0.01 * w))         # horizontal connect
    kh = max(1, int(0.004 * h))        # tiny vertical tolerance
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
    blobs = cv2.dilate(inv, kernel, iterations=1)

    _, binimg = cv2.threshold(blobs, 0, 255, cv2.THRESH_BINARY)
    num, _, stats, _ = cv2.connectedComponentsWithStats(binimg, connectivity=8)

    boxes: List[Tuple[int, int, int, int]] = []
    page_area = w * h
    min_area = max(30, int(1e-5 * page_area))
    for i in range(1, num):  # skip background
        x, y, ww, hh, area = stats[i]
        if area < min_area:
            continue
        if ww < 2 or hh < 2:
            continue
        # avoid absurdly tall/skinny artifacts
        if hh > 0 and (ww / float(hh)) < 0.2:
            continue
        boxes.append((x, y, x + ww, y + hh))

    boxes.sort(key=lambda b: (0.5 * (b[1] + b[3]), b[0]))
    return boxes


# -----------------------
# 1-D k-means on y-centers (robust line grouping)
# -----------------------

def _kmeans_1d(y: np.ndarray, k: int, iters: int = 30) -> np.ndarray:
    """
    Simple 1-D k-means returning cluster labels (0..k-1).
    Uses percentile-spaced init to avoid bad starts; empty clusters are re-assigned.
    """
    n = y.size
    if k <= 1 or n == 0:
        return np.zeros(n, dtype=int)
    y_sorted = np.sort(y)
    # Percentile-based init (monotonic)
    qs = np.linspace(0, 1, num=k, endpoint=False) + (0.5 / k)
    centers = np.quantile(y_sorted, qs).astype(float)

    labels = np.zeros(n, dtype=int)
    for _ in range(max(1, iters)):
        # assign
        d = np.abs(y[:, None] - centers[None, :])
        labels = np.argmin(d, axis=1)

        # recompute
        changed = False
        for j in range(k):
            idx = np.where(labels == j)[0]
            if idx.size == 0:
                # re-seed to the farthest point from existing centers
                far_idx = int(np.argmax(np.min(np.abs(y[:, None] - centers[None, :]), axis=1)))
                centers[j] = float(y[far_idx])
                changed = True
            else:
                c_new = float(np.median(y[idx]))
                if c_new != centers[j]:
                    centers[j] = c_new
                    changed = True
        if not changed:
            break
    return labels


# -----------------------
# Public API: aligned boxes
# -----------------------

def extract_line_boxes_aligned(
    image_bytes: bytes,
    line_count: int,
    *,
    prefer_aspect_columns: bool = True,
    allow_valley_fallback: bool = True,
    x_left_pct: float = 5.0,             # robust left bound percentile per line
    x_right_pct: float = 95.0,           # robust right bound percentile per line
    pad_x_frac: float = 0.01,            # horizontal padding relative to page width
    pad_y_frac: float = 0.06,            # vertical padding relative to median word height
    min_h_factor: float = 0.6,           # min line height factor * median word height
    max_h_factor: float = 2.5,           # max line height factor * median word height
) -> List[Dict[str, float]]:
    """
    Build exactly `line_count` line boxes using:
      - aspect/valley split into 1–2 columns,
      - word detection,
      - per-column 1-D k-means clustering on word center-y into the requested number of lines,
      - robust percentiles for left/right per line, min/max y with padding,
      - hard clamps and monotonic Y guard.
    This strongly decouples lines; a bad line won't stretch neighbours.
    """
    if not image_bytes or line_count <= 0:
        return []

    img = _load_image_from_bytes(image_bytes)
    if img is None:
        return []

    inv = _best_inv(img)
    h, w = inv.shape[:2]

    # Columns
    n_cols = _guess_columns_by_aspect(w, h) if prefer_aspect_columns else 1
    split_x = _center_valley(inv) if (allow_valley_fallback and n_cols >= 2) else None
    if n_cols == 1 or split_x is None:
        segs = [(0, w)]
    else:
        segs = [(0, split_x), (split_x, w)]

    # Words and median word height
    words = _word_boxes(inv)
    if not words:
        # fallback: even strips
        return synthesize_line_boxes(line_count)

    med_word_h = float(np.median([b[3] - b[1] for b in words])) if words else max(1.0, h / (line_count * 1.5))
    min_line_h = max(1.0, min_h_factor * med_word_h)
    max_line_h = max(min_line_h + 1.0, max_h_factor * med_word_h)

    # Split words per segment
    words_per_seg: List[List[Tuple[int,int,int,int]]] = []
    for (x0, x1) in segs:
        cx0, cx1 = x0, x1
        words_per_seg.append([b for b in words if (b[0] + b[2]) * 0.5 >= cx0 and (b[0] + b[2]) * 0.5 < cx1])

    # Distribute requested lines across segments by word count (simple, stable)
    counts = []
    total_words = sum(len(ws) for ws in words_per_seg) or 1
    for ws in words_per_seg:
        counts.append(int(np.floor(line_count * (len(ws) / total_words))))
    # fix to exact sum
    diff = line_count - sum(counts)
    order = np.argsort([-len(ws) for ws in words_per_seg])
    for i in range(abs(diff)):
        counts[order[i % len(order)]] += 1 if diff > 0 else -1
    # ensure non-negative
    for i in range(len(counts)):
        if counts[i] < 0: counts[i] = 0
    if sum(counts) != line_count:
        counts[0] += (line_count - sum(counts))

    boxes_px: List[Tuple[int,int,int,int]] = []
    px_pad = max(1, int(pad_x_frac * w))
    py_pad = max(1, int(pad_y_frac * med_word_h))

    for (x0_seg, x1_seg), nL, ws in zip(segs, counts, words_per_seg):
        if nL <= 0:
            continue
        if not ws:
            # synthesize evenly in this segment
            for i in range(nL):
                y0 = int((i / nL) * h)
                y1 = int(((i + 1) / nL) * h)
                boxes_px.append((x0_seg + px_pad, max(0, y0 + py_pad), x1_seg - px_pad, min(h, y1 - py_pad)))
            continue

        ycenters = np.array([0.5 * (b[1] + b[3]) for b in ws], dtype=np.float64)
        labels = _kmeans_1d(ycenters, nL, iters=40) if nL > 1 else np.zeros(len(ws), dtype=int)

        # For each cluster (line), build robust box
        for c in range(nL):
            idx = np.where(labels == c)[0]
            if idx.size == 0:
                # synthesize thin strip in this segment at expected slot
                y0 = int((c / nL) * h)
                y1 = int(min(h, y0 + max(1, int(0.9 * med_word_h))))
                boxes_px.append((x0_seg + px_pad, y0, x1_seg - px_pad, y1))
                continue

            words_c = [ws[i] for i in idx]
            xs_l = np.array([b[0] for b in words_c], dtype=np.float64)
            xs_r = np.array([b[2] for b in words_c], dtype=np.float64)
            ys_t = np.array([b[1] for b in words_c], dtype=np.float64)
            ys_b = np.array([b[3] for b in words_c], dtype=np.float64)

            left = int(np.percentile(xs_l, x_left_pct))  - px_pad
            right = int(np.percentile(xs_r, x_right_pct)) + px_pad
            top = int(np.min(ys_t)) - py_pad
            bottom = int(np.max(ys_b)) + py_pad

            # Clamp to segment/page bounds
            left = max(x0_seg, left)
            right = min(x1_seg, right)
            if right <= left: right = left + 1
            top = max(0, top)
            bottom = min(h, bottom)
            if bottom <= top: bottom = top + 1

            # Height clamps (decouple runaway lines)
            line_h = float(bottom - top)
            if line_h < min_line_h:
                need = int(np.ceil(min_line_h - line_h))
                grow_up = need // 2
                grow_dn = need - grow_up
                top = max(0, top - grow_up)
                bottom = min(h, bottom + grow_dn)
            elif line_h > max_line_h:
                cut = int(np.floor(line_h - max_line_h))
                cut_up = cut // 2
                cut_dn = cut - cut_up
                top = min(bottom - 1, top + cut_up)
                bottom = max(top + 1, bottom - cut_dn)

            # Final clamp
            top = max(0, min(top, h - 2))
            bottom = max(top + 1, min(bottom, h))
            left = max(x0_seg, min(left, x1_seg - 2))
            right = max(left + 1, min(right, x1_seg))

            boxes_px.append((left, top, right, bottom))

    # Reading order L->R, then T->B
    boxes_px.sort(key=lambda b: ((b[0] + b[2]) * 0.5, b[1]))

    # Enforce mild monotonic Y (avoid tiny overlaps between neighbours)
    boxes_sorted = sorted(boxes_px, key=lambda b: (b[1], b[0]))
    for i in range(1, len(boxes_sorted)):
        p = list(boxes_sorted[i - 1])
        c = list(boxes_sorted[i])
        if c[1] < p[3]:
            c[1] = p[3]
            if c[3] <= c[1]:
                c[3] = c[1] + 1
            boxes_sorted[i] = tuple(c)
    boxes_px = boxes_sorted

    # Normalize and match requested count
    boxes_norm: List[Dict[str, float]] = []
    inv_h = 1.0 / float(h) if h else 1.0
    inv_w = 1.0 / float(w) if w else 1.0
    for (x0, y0, x1, y1) in boxes_px[:line_count]:
        boxes_norm.append({
            "x": x0 * inv_w,
            "y": y0 * inv_h,
            "width": max(1, x1 - x0) * inv_w,
            "height": max(1, y1 - y0) * inv_h,
        })
    while len(boxes_norm) < line_count:
        boxes_norm.append({"x": 0.05, "y": 0.05 + 0.03 * len(boxes_norm), "width": 0.90, "height": 0.03})

    # Final monotonic guard in normalized space
    eps = 1e-6
    last_y = -1.0
    for b in boxes_norm:
        if b["y"] <= last_y:
            b["y"] = min(1.0 - eps, last_y + max(eps, 0.5 * b["height"]))
        last_y = b["y"]

    return boxes_norm


# -----------------------
# Legacy simple contour method
# -----------------------

def extract_line_boxes(
    image_bytes: bytes,
    *,
    min_area: int = 2000,
    min_area_ratio: float = 3e-4,
    suppress_rules: bool = True,
) -> List[Dict[str, float]]:
    """
    Simple contour-based approximation kept for backward compatibility.
    Prefer extract_line_boxes_aligned for accurate per-line boxes.
    """
    img = _load_image_from_bytes(image_bytes)
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binarized = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = 255 - binarized

    h, w = img.shape[:2]

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
    return boxes


# -----------------------
# Fallback: even strips
# -----------------------

def synthesize_line_boxes(line_count: int, *, margin: float = 0.04) -> List[Dict[str, float]]:
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
