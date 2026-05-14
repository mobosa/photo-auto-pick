"""Composition analysis: rule of thirds, symmetry, horizon, negative space.

Optimized: accepts pre-computed intermediates to eliminate redundant
Canny (3x), HoughLinesP (2x), and color conversions (6x).
"""

import cv2
import numpy as np


def analyze_rule_of_thirds(gray: np.ndarray, edges_1mp: np.ndarray) -> float:
    """Check if strong edges/saliency fall near thirds intersections.
    Uses 1MP edges for speed (saliency is resolution-insensitive).
    """
    h, w = gray.shape

    third_h = [h // 3, 2 * h // 3]
    third_w = [w // 3, 2 * w // 3]

    margin = int(min(h, w) * 0.08)
    score = 0.0
    total_weight = 0.0

    # Scale thirds coordinates to 1MP space
    h1, w1 = edges_1mp.shape
    sy, sx = h1 / h, w1 / w

    for y in third_h:
        y1 = int((y - margin) * sy)
        y2 = int((y + margin) * sy)
        roi = edges_1mp[max(0, y1):min(h1, y2), :]
        score += roi.mean() / 255.0
        total_weight += 1.0

    for x in third_w:
        x1 = int((x - margin) * sx)
        x2 = int((x + margin) * sx)
        roi = edges_1mp[:, max(0, x1):min(w1, x2)]
        score += roi.mean() / 255.0
        total_weight += 1.0

    if total_weight > 0:
        score /= total_weight

    # Saliency check (on 1MP gray for speed)
    try:
        gray_1mp_small = cv2.resize(gray, (w1, h1),
                                    interpolation=cv2.INTER_AREA)
        saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
        success, saliency_map = saliency.computeSaliency(gray_1mp_small)
        if success:
            saliency_map = (saliency_map * 255).astype(np.uint8)
            _, thresh = cv2.threshold(saliency_map, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            moments = cv2.moments(thresh)
            if moments["m00"] > 0:
                cx = int(moments["m10"] / moments["m00"] / sx)
                cy = int(moments["m01"] / moments["m00"] / sy)
                min_dist = float("inf")
                for ty in third_h:
                    for tx in third_w:
                        dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
                        min_dist = min(min_dist, dist)
                max_dist = (w ** 2 + h ** 2) ** 0.5
                thirds_bonus = 1.0 - min_dist / max_dist
                score = score * 0.5 + thirds_bonus * 0.5
    except (AttributeError, cv2.error):
        pass

    return max(0.0, min(100.0, score * 200))


def analyze_symmetry(gray: np.ndarray) -> float:
    """Measure horizontal and vertical symmetry (full-res for precision)."""
    h, w = gray.shape

    left = gray[:, :w // 2]
    right = np.flip(gray[:, w - w // 2:], axis=1)
    min_w = min(left.shape[1], right.shape[1])
    left = left[:, :min_w]
    right = right[:, :min_w]
    v_diff = np.mean(np.abs(left.astype(float) - right.astype(float))) / 255.0

    top = gray[:h // 2, :]
    bottom = np.flip(gray[h - h // 2:, :], axis=0)
    min_h = min(top.shape[0], bottom.shape[0])
    top = top[:min_h, :]
    bottom = bottom[:min_h, :]
    h_diff = np.mean(np.abs(top.astype(float) - bottom.astype(float))) / 255.0

    v_score = max(0, 1.0 - v_diff * 4)
    h_score = max(0, 1.0 - h_diff * 4)

    score = max(v_score, h_score)
    return max(0.0, min(100.0, score * 100))


def analyze_horizon_level(gray: np.ndarray, edges: np.ndarray) -> float:
    """Detect and score horizon line levelness.
    Uses full-res edges for line detection precision.
    """
    h, w = gray.shape
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                            minLineLength=w // 4, maxLineGap=20)

    if lines is None:
        return 70.0

    horizontal_angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle < 15 or angle > 165:
            horizontal_angles.append(angle if angle < 90 else 180 - angle)

    if not horizontal_angles:
        return 70.0

    avg_angle = np.mean(horizontal_angles)
    score = max(0, 1.0 - avg_angle / 5.0)
    return max(0.0, min(100.0, score * 100))


def analyze_negative_space(gray: np.ndarray) -> float:
    """Evaluate if photo has breathing room (negative space)."""
    h, w = gray.shape
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    bg_ratio = (thresh == 0).sum() / (h * w)
    if bg_ratio > 0.5:
        bg_ratio = 1.0 - bg_ratio

    if 0.20 <= bg_ratio <= 0.60:
        score = 1.0
    elif bg_ratio < 0.20:
        score = bg_ratio / 0.20
    else:
        score = max(0, 1.0 - (bg_ratio - 0.60) / 0.40)

    return max(0.0, min(100.0, score * 100))


def analyze_leading_lines(gray: np.ndarray, edges: np.ndarray) -> float:
    """Detect leading lines that guide the viewer's eye.
    Uses full-res edges with its own HoughLinesP parameters.
    """
    h, w = gray.shape
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                            minLineLength=w // 5, maxLineGap=30)
    if lines is None:
        return 40.0

    cx, cy = w // 2, h // 2
    convergent = 0
    checked = min(len(lines), 30)
    for line in lines[:30]:
        x1, y1, x2, y2 = line[0]
        mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
        dist_to_center = ((mid_x - cx) ** 2 + (mid_y - cy) ** 2) ** 0.5
        max_dist = (w ** 2 + h ** 2) ** 0.5 / 2
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        is_diagonal = 15 < angle < 75 or 105 < angle < 165
        if is_diagonal or dist_to_center < max_dist * 0.5:
            convergent += 1
    score = min(1.0, convergent / max(1, checked))
    return max(0.0, min(100.0, score * 100))


def analyze_depth_of_field(gray_1mp: np.ndarray) -> float:
    """Evaluate depth of field using 1MP gray.
    The CV metric is resolution-independent by construction.
    """
    h, w = gray_1mp.shape
    lap_vars = []
    for r in range(3):
        for c in range(3):
            y1, y2 = r * h // 3, (r + 1) * h // 3
            x1, x2 = c * w // 3, (c + 1) * w // 3
            cell = gray_1mp[y1:y2, x1:x2]
            lap_vars.append(cv2.Laplacian(cell, cv2.CV_64F).var())
    lap_vars = np.array(lap_vars)
    if lap_vars.mean() == 0:
        return 40.0
    cv_sharpness = lap_vars.std() / (lap_vars.mean() + 1e-6)
    if 0.2 <= cv_sharpness <= 1.5:
        score = 0.7 + 0.3 * min(1.0, cv_sharpness / 1.0)
    elif cv_sharpness < 0.2:
        score = 0.4 + cv_sharpness * 1.5
    else:
        score = max(0.3, 1.0 - (cv_sharpness - 1.5) / 2.0)
    return max(0.0, min(100.0, score * 100))


def compute_composition_score(inter) -> dict:
    """Run all composition analyses using pre-computed intermediates."""
    thirds = analyze_rule_of_thirds(inter.gray, inter.edges_1mp)
    symmetry = analyze_symmetry(inter.gray)
    horizon = analyze_horizon_level(inter.gray, inter.edges)
    neg_space = analyze_negative_space(inter.gray)
    leading = analyze_leading_lines(inter.gray, inter.edges)
    dof = analyze_depth_of_field(inter.gray_1mp)

    overall = (
        thirds * 0.25 + symmetry * 0.15 + horizon * 0.15 +
        neg_space * 0.15 + leading * 0.15 + dof * 0.15
    )

    return {
        "rule_of_thirds": round(thirds, 2),
        "symmetry": round(symmetry, 2),
        "horizon_level": round(horizon, 2),
        "negative_space": round(neg_space, 2),
        "leading_lines": round(leading, 2),
        "depth_of_field": round(dof, 2),
        "overall": round(overall, 2),
    }
