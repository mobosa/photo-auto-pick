"""Technical quality analysis: exposure, color, sharpness, noise,
   dynamic range, focus quality, color richness.

Optimized: accepts pre-computed intermediates (gray, HSV, downscaled)
to eliminate redundant color conversions.
"""

import cv2
import numpy as np


# --- Resolution normalization ---
_REF_PIXELS = 2_000_000  # 2 MP reference


def _pixel_scale(shape) -> float:
    """Return a multiplier to normalize resolution-dependent metrics."""
    h, w = shape[:2]
    return max(1.0, (h * w) / _REF_PIXELS)


def analyze_exposure(gray: np.ndarray) -> float:
    """Score 0-100 based on histogram distribution + clipping penalty."""
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    total = hist.sum()
    if total == 0:
        return 0.0
    dark_ratio = hist[:16].sum() / total
    bright_ratio = hist[240:].sum() / total
    mid_ratio = hist[32:224].sum() / total

    base = mid_ratio * 70
    clip_penalty = (dark_ratio + bright_ratio) * 70
    score = max(0.0, base - clip_penalty + 30)

    # Additional penalty for severe clipping (>5% in extreme bins)
    shadow_clip = hist[:5].sum() / total
    highlight_clip = hist[250:].sum() / total
    if shadow_clip > 0.05:
        score -= (shadow_clip - 0.05) * 200
    if highlight_clip > 0.05:
        score -= (highlight_clip - 0.05) * 200

    return max(0.0, min(100.0, score))


def analyze_color(bgr: np.ndarray, hsv: np.ndarray) -> float:
    """Score 0-100 based on color balance and saturation."""
    if len(bgr.shape) != 3:
        return 50.0
    b, g, r = cv2.split(bgr)
    r_mean, g_mean, b_mean = r.mean(), g.mean(), b.mean()
    overall_mean = (r_mean + g_mean + b_mean) / 3
    if overall_mean > 0:
        balance = 1.0 - (
            abs(r_mean - overall_mean) +
            abs(g_mean - overall_mean) +
            abs(b_mean - overall_mean)
        ) / (3 * overall_mean)
    else:
        balance = 0.0
    sat_mean = hsv[:, :, 1].mean() / 255.0
    if 0.15 <= sat_mean <= 0.65:
        sat_score = 1.0
    elif sat_mean < 0.15:
        sat_score = sat_mean / 0.15
    else:
        sat_score = max(0, 1.0 - (sat_mean - 0.65) / 0.35)
    score = balance * 50 + sat_score * 50
    return max(0.0, min(100.0, score * 100))


def analyze_sharpness(gray: np.ndarray) -> float:
    """Score 0-100 based on Laplacian variance + Tenengrad gradient.
    Uses pre-computed gray (typically 1MP for speed).
    """
    scale = _pixel_scale(gray.shape)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    tenengrad = (gx ** 2 + gy ** 2).mean()
    lap_score = min(1.0, lap_var / (800 * scale))
    ten_score = min(1.0, tenengrad / (1500 * scale))
    return max(0.0, min(100.0, (lap_score * 60 + ten_score * 40) * 100))


def analyze_noise(gray: np.ndarray, iso: int = 0) -> float:
    """Score 0-100, higher = less noise.
    Uses pre-computed gray (typically 1MP). ISO-aware threshold.
    """
    # Further downscale if needed (1MP -> 800px max)
    h, w = gray.shape
    max_side = 800
    if max(h, w) > max_side:
        s = max_side / max(h, w)
        gray = cv2.resize(gray, (int(w * s), int(h * s)))
    median = cv2.medianBlur(gray, 5)
    diff = cv2.absdiff(gray, median).astype(float)
    noise_level = np.median(diff)
    # ISO-aware threshold: high-ISO images get a more lenient threshold
    if iso > 3200:
        threshold = 25.0
    elif iso > 1600:
        threshold = 20.0
    else:
        threshold = 15.0
    score = max(0.0, 1.0 - noise_level / threshold)
    return max(0.0, min(100.0, score * 100))


def analyze_dynamic_range(gray: np.ndarray) -> float:
    """Score 0-100: how much of the tonal range is used."""
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    total = hist.sum()
    if total == 0:
        return 0.0
    non_empty = np.count_nonzero(hist)
    cumulative = np.cumsum(hist)
    p5 = np.searchsorted(cumulative, total * 0.05)
    p95 = np.searchsorted(cumulative, total * 0.95)
    effective_range = p95 - p5
    range_score = min(1.0, effective_range / 180)
    spread_score = min(1.0, non_empty / 200)
    return max(0.0, min(100.0, (range_score * 60 + spread_score * 40) * 100))


def analyze_focus_quality(gray: np.ndarray) -> float:
    """Score 0-100: FFT-based focus/sharpness quality.
    Uses pre-computed gray, further resized to 512px for FFT.
    """
    h, w = gray.shape
    max_dim = 512
    if max(h, w) > max_dim:
        s = max_dim / max(h, w)
        gray = cv2.resize(gray, (int(w * s), int(h * s)))
    f = np.fft.fft2(gray.astype(np.float64))
    fshift = np.fft.fftshift(f)
    magnitude = np.log1p(np.abs(fshift))
    rows, cols = magnitude.shape
    cy, cx = rows // 2, cols // 2
    r = min(rows, cols) // 16
    y, x = np.ogrid[:rows, :cols]
    low_mask = ((x - cx) ** 2 + (y - cy) ** 2) <= r ** 2
    low_energy = magnitude[low_mask].sum()
    total_energy = magnitude.sum()
    if total_energy == 0:
        return 0.0
    high_ratio = 1.0 - low_energy / total_energy
    score = (min(high_ratio, 0.50) - 0.10) / 0.40
    return max(0.0, min(100.0, score * 100))


def analyze_color_richness(hsv: np.ndarray) -> float:
    """Score 0-100: diversity of colors in the image."""
    hue_hist = cv2.calcHist([hsv], [0], None, [36], [0, 180]).flatten()
    total = hue_hist.sum()
    if total == 0:
        return 0.0
    significant = np.count_nonzero(hue_hist > total * 0.01)
    score = min(1.0, significant / 12)
    sat_std = hsv[:, :, 1].std() / 128.0
    return max(0.0, min(100.0, (score * 70 + min(1.0, sat_std) * 30) * 100))


def compute_technical_score(inter, iso: int = 0) -> dict:
    """Run all technical analyses using pre-computed intermediates."""
    exposure = analyze_exposure(inter.gray)
    color = analyze_color(inter.bgr_full, inter.hsv)
    sharpness = analyze_sharpness(inter.gray_1mp)
    noise = analyze_noise(inter.gray_1mp, iso=iso)
    dynamic_range = analyze_dynamic_range(inter.gray)
    focus_quality = analyze_focus_quality(inter.gray_1mp)
    color_richness = analyze_color_richness(inter.hsv)

    overall = (
        exposure * 0.20 +
        color * 0.15 +
        sharpness * 0.20 +
        noise * 0.15 +
        dynamic_range * 0.10 +
        focus_quality * 0.10 +
        color_richness * 0.10
    )

    return {
        "exposure": round(exposure, 2),
        "color": round(color, 2),
        "sharpness": round(sharpness, 2),
        "noise": round(noise, 2),
        "dynamic_range": round(dynamic_range, 2),
        "focus_quality": round(focus_quality, 2),
        "color_richness": round(color_richness, 2),
        "overall": round(overall, 2),
    }
