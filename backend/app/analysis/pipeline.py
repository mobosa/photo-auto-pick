"""Analysis pipeline: orchestrates all analysis modules for a single photo.

Performance optimization: builds shared intermediates (gray, HSV, edges,
downscaled copies) ONCE and passes them to all modules, eliminating
~27 redundant full-resolution color conversions per photo.
"""

import cv2
import numpy as np
from dataclasses import dataclass

from app.models.schemas import (
    PhotoResult, TechnicalScores, CompositionScores,
    SemanticScores, AestheticScores, ExifInfo,
)
from app.utils.image_io import load_image_cv, extract_exif


# ---------------------------------------------------------------------------
# Shared intermediates — pre-computed once per photo
# ---------------------------------------------------------------------------

@dataclass
class ImageIntermediates:
    """Pre-computed image data shared across all analysis modules."""
    bgr_full: np.ndarray          # original full-res BGR
    gray: np.ndarray              # BGR2GRAY, full-res
    hsv: np.ndarray               # BGR2HSV, full-res
    edges: np.ndarray             # Canny(gray, 50, 150), full-res
    bgr_1mp: np.ndarray           # downsampled to max ~1000px side
    gray_1mp: np.ndarray
    hsv_1mp: np.ndarray
    edges_1mp: np.ndarray
    nima_tensor: np.ndarray       # (1, 3, 224, 224) float32, pre-normalized


def build_intermediates(bgr: np.ndarray) -> ImageIntermediates:
    """Pre-compute all shared arrays from the BGR image."""
    h, w = bgr.shape[:2]

    # Full-res conversions (computed ONCE)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    edges = cv2.Canny(gray, 50, 150)

    # 1MP downsample (max side ~1000px)
    max_side = 1000
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        bgr_1mp = cv2.resize(bgr, (int(w * scale), int(h * scale)),
                             interpolation=cv2.INTER_AREA)
    else:
        bgr_1mp = bgr
    gray_1mp = cv2.cvtColor(bgr_1mp, cv2.COLOR_BGR2GRAY)
    hsv_1mp = cv2.cvtColor(bgr_1mp, cv2.COLOR_BGR2HSV)
    edges_1mp = cv2.Canny(gray_1mp, 50, 150)

    # NIMA 224x224 preprocessing (avoids full-res PIL allocation)
    rgb_224 = cv2.cvtColor(
        cv2.resize(bgr, (224, 224), interpolation=cv2.INTER_LANCZOS4),
        cv2.COLOR_BGR2RGB,
    )
    arr = (rgb_224.astype(np.float32) / 127.5 - 1.0).transpose(2, 0, 1)
    nima_tensor = arr[np.newaxis, ...]

    return ImageIntermediates(
        bgr_full=bgr, gray=gray, hsv=hsv, edges=edges,
        bgr_1mp=bgr_1mp, gray_1mp=gray_1mp, hsv_1mp=hsv_1mp,
        edges_1mp=edges_1mp, nima_tensor=nima_tensor,
    )


# ---------------------------------------------------------------------------
# Scene-specific weight profiles: (tech, comp, semantic, aesthetic, uniqueness)
# ---------------------------------------------------------------------------

_SCENE_PROFILES = {
    "portrait":     (0.15, 0.18, 0.20, 0.35, 0.12),
    "sunset":       (0.15, 0.28, 0.22, 0.25, 0.10),
    "landscape":    (0.20, 0.32, 0.13, 0.25, 0.10),
    "forest":       (0.20, 0.28, 0.18, 0.24, 0.10),
    "water":        (0.20, 0.28, 0.18, 0.24, 0.10),
    "night":        (0.28, 0.22, 0.13, 0.25, 0.12),
    "architecture": (0.20, 0.32, 0.13, 0.25, 0.10),
    "street":       (0.20, 0.23, 0.18, 0.28, 0.11),
    "indoor":       (0.25, 0.18, 0.18, 0.28, 0.11),
    "macro":        (0.28, 0.23, 0.13, 0.25, 0.11),
}
_DEFAULT_PROFILE = (0.22, 0.25, 0.15, 0.28, 0.10)


def get_blended_weights(scene_labels: list[tuple[str, float]]) -> tuple[float, float, float, float, float]:
    """Blend scene weight profiles by confidence. scene_labels = [(scene, conf), ...]."""
    import numpy as _np
    if not scene_labels:
        return _DEFAULT_PROFILE
    blended = _np.zeros(5)
    total_conf = sum(c for _, c in scene_labels)
    if total_conf == 0:
        return _DEFAULT_PROFILE
    for scene, conf in scene_labels:
        w = _np.array(_SCENE_PROFILES.get(scene, _DEFAULT_PROFILE))
        blended += w * (conf / total_conf)
    return tuple(float(x) for x in blended)


def compute_final_score(result: PhotoResult, scene_labels: list[tuple[str, float]] = None) -> PhotoResult:
    """Compute weighted final score using geometric mean (prevents one low dimension from being masked)."""
    import numpy as _np
    if scene_labels:
        tech_w, comp_w, sem_w, aesth_w, uniq_w = get_blended_weights(scene_labels)
    else:
        scene = result.semantic.scene if result.semantic.scene else ""
        tech_w, comp_w, sem_w, aesth_w, uniq_w = _SCENE_PROFILES.get(scene, _DEFAULT_PROFILE)

    weights = _np.array([tech_w, comp_w, sem_w, aesth_w, uniq_w])
    scores = _np.array([
        max(1.0, result.technical.overall),
        max(1.0, result.composition.overall),
        max(1.0, result.semantic.overall),
        max(1.0, result.aesthetic.overall),
        max(1.0, result.uniqueness),
    ])

    total_w = weights.sum()
    if total_w == 0:
        total_w = 1.0

    # Weighted geometric mean: exp(sum(w_i * ln(s_i)) / sum(w_i))
    log_sum = (weights * _np.log(scores)).sum()
    final = float(_np.exp(log_sum / total_w))

    result.final_score = round(final, 2)
    result.grade = _score_to_grade(final)

    return result


def _score_to_grade(score: float) -> str:
    """Convert 0-100 score to 7-grade system: S/A/B+/B/C+/C/D."""
    if score >= 90:
        return "S"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B+"
    if score >= 60:
        return "B"
    if score >= 50:
        return "C+"
    if score >= 40:
        return "C"
    return "D"


def analyze_single_photo(filepath: str, task_id: str) -> tuple[PhotoResult, str]:
    """Run full analysis pipeline on a single photo.
    Returns (PhotoResult, image_hash).
    """
    from app.analysis.technical import compute_technical_score
    from app.analysis.composition import compute_composition_score
    from app.analysis.semantic import compute_semantic_score, compute_image_hash
    from app.analysis.aesthetic import compute_aesthetic_score
    from pathlib import Path

    img = load_image_cv(filepath)
    if img is None:
        return PhotoResult(
            filename=Path(filepath).name,
            filepath=filepath,
            task_id=task_id,
        ), ""

    # Build all shared intermediates ONCE
    inter = build_intermediates(img)

    result = PhotoResult(
        filename=Path(filepath).name,
        filepath=filepath,
        task_id=task_id,
    )

    exif = extract_exif(filepath)
    result.exif = ExifInfo(**exif)

    # Parse ISO for noise analysis
    try:
        iso_val = int(exif.get("iso", "0") or "0")
    except (ValueError, TypeError):
        iso_val = 0

    result.technical = TechnicalScores(**compute_technical_score(inter, iso=iso_val))
    result.composition = CompositionScores(**compute_composition_score(inter))

    semantic_data = compute_semantic_score(inter)
    result.semantic = SemanticScores(
        scene=semantic_data["scene"],
        mood=semantic_data["mood"],
        tags=semantic_data["tags"],
        overall=semantic_data["overall"],
    )
    import json as _json
    result.face_json = _json.dumps(semantic_data.get("faces", []))

    result.aesthetic = AestheticScores(**compute_aesthetic_score(inter))

    result.uniqueness = 70.0  # placeholder; computed in batch after all hashes collected

    scene_labels = semantic_data.get("scene_labels", [])
    result = compute_final_score(result, scene_labels)
    result.suggestions = generate_suggestions(result)

    # Hash from 1MP image (phash internally resizes to 8x8 anyway)
    phash = compute_image_hash(inter)

    return result, phash


def compute_uniqueness(results: list, hashes: dict[str, str]) -> None:
    """Compute uniqueness for each photo based on pHash Hamming distance + EXIF bonus.

    uniqueness = 0.5 * pHash_uniqueness + 0.5 * exif_bonus
    """
    try:
        import imagehash
    except ImportError:
        imagehash = None

    parsed: dict[int, "imagehash.ImageHash"] = {}
    if imagehash:
        for i, r in enumerate(results):
            h = hashes.get(r.filepath, "")
            if h:
                try:
                    parsed[i] = imagehash.hex_to_hash(h)
                except Exception:
                    pass

    for i, r in enumerate(results):
        # pHash component
        if i not in parsed:
            phash_score = 70.0
        else:
            min_dist = float('inf')
            for j, other_hash in parsed.items():
                if i == j:
                    continue
                dist = parsed[i] - other_hash
                min_dist = min(min_dist, dist)
            if min_dist == float('inf'):
                phash_score = 70.0
            else:
                phash_score = min(100.0, max(0.0, (min_dist / 32.0) * 100.0))

        # EXIF bonus component
        exif_score = compute_exif_bonus(r.exif)

        # Blend: 50% pHash uniqueness, 50% EXIF bonus
        r.uniqueness = round(phash_score * 0.5 + exif_score * 0.5, 2)


def compute_exif_bonus(exif: ExifInfo) -> float:
    """Compute 0-100 bonus score from EXIF metadata.
    Rewards deliberate photographic choices (golden hour, specific focal length, etc.)
    """
    bonus = 50.0  # baseline

    # ISO quality indicator: lower ISO = cleaner capture
    try:
        iso = int(exif.iso or "0")
    except (ValueError, TypeError):
        iso = 0
    if 0 < iso <= 400:
        bonus += 10.0
    elif iso > 3200:
        bonus -= 10.0

    # Golden hour shooting (datetime_original)
    try:
        if exif.datetime_original:
            # Format: "YYYY:MM:DD HH:MM:SS"
            time_part = exif.datetime_original.split(" ")[-1] if " " in exif.datetime_original else ""
            if time_part:
                hour = int(time_part.split(":")[0])
                # Golden hour: 5-8 AM or 5-8 PM
                if 5 <= hour <= 8 or 17 <= hour <= 20:
                    bonus += 10.0
    except (IndexError, ValueError):
        pass

    # Focal length: deliberate lens choice
    try:
        focal = float(exif.focal_length_35mm or "0")
    except (ValueError, TypeError):
        focal = 0.0
    if focal > 0:
        # Long telephoto (>100mm) or ultra-wide (<24mm) = deliberate choice
        if focal > 100 or focal < 24:
            bonus += 8.0
        # Normal range is fine too
        elif 35 <= focal <= 85:
            bonus += 5.0

    # Aperture: wide aperture = deliberate creative choice
    try:
        aperture_str = (exif.aperture or "").replace("f/", "").replace("F/", "").strip()
        aperture = float(aperture_str)
    except (ValueError, TypeError):
        aperture = 0.0
    if 0 < aperture <= 2.8:
        bonus += 8.0
    elif 2.8 < aperture <= 5.6:
        bonus += 4.0

    # Exposure compensation: non-zero EV = deliberate exposure choice
    try:
        ev_str = (exif.exposure_comp or "").replace("+", "").strip()
        ev = float(ev_str)
        if ev != 0.0:
            bonus += 5.0
    except (ValueError, TypeError):
        pass

    return max(0.0, min(100.0, bonus))


# ---------------------------------------------------------------------------
# Grade descriptions & suggestions
# ---------------------------------------------------------------------------

_GRADE_INFO = {
    "S":  "顶级 — 专业级作品，极力推荐",
    "A":  "优秀 — 直接可用，强烈推荐",
    "B+": "良好 — 质量上乘，推荐使用",
    "B":  "中等偏上 — 质量不错，可挑选使用",
    "C+": "中等 — 有一定瑕疵，挑选使用",
    "C":  "一般 — 瑕疵较多，谨慎使用",
    "D":  "较差 — 不建议使用",
}


def generate_suggestions(result: PhotoResult) -> str:
    """Generate improvement suggestions based on individual dimension scores."""
    tips = []
    t = result.technical
    c = result.composition
    s = result.semantic

    grade_desc = _GRADE_INFO.get(result.grade, "")
    tips.append(f"等级 {result.grade}：{grade_desc}")

    # Technical suggestions
    if t.exposure < 50:
        tips.append("曝光不足或过曝：建议调整曝光补偿(EV)，或在后期软件中修正亮度/高光/阴影")
    if t.sharpness < 50:
        tips.append("画面偏软/模糊：检查对焦是否准确，或使用三脚架减少抖动")
    if t.noise < 50:
        tips.append("噪点较多：降低ISO感光度，或在后期中使用降噪工具")
    if t.dynamic_range < 50:
        tips.append("动态范围窄：尝试拍摄RAW格式，后期可恢复更多亮部/暗部细节")
    if t.focus_quality < 50:
        tips.append("对焦质量低：确认对焦点落在主体上，可使用单点对焦模式")
    if t.color_richness < 40:
        tips.append("色彩偏单调：可尝试调整白平衡或饱和度，或寻找色彩更丰富的拍摄角度")

    # Composition suggestions
    if c.rule_of_thirds < 40:
        tips.append("构图偏中心：尝试将主体放在画面三分线交叉点上，开启相机网格线辅助构图")
    if c.horizon_level < 50:
        tips.append("水平线倾斜：使用相机内置水平仪，或在后期中拉直地平线")
    if c.symmetry < 30:
        tips.append("对称性不足（如非刻意不对称）：检查画面左右/上下是否失衡")
    if c.negative_space < 30:
        tips.append("画面过满：适当留白可以让主体更突出，给画面呼吸感")
    if c.depth_of_field < 40:
        tips.append("景深平淡：尝试使用大光圈(f/1.8-2.8)虚化背景，突出主体")

    # Semantic suggestions
    if s.scene in ("night",) and t.exposure < 60:
        tips.append("夜景拍摄：使用三脚架+长曝光，或提高ISO配合降噪")

    # Aesthetic suggestions
    ae = result.aesthetic
    if ae.method == "nima" and ae.nima_score < 50:
        tips.append("美学评分偏低：整体视觉吸引力不足，可尝试改善构图、光线或色彩搭配")
    if ae.contrast < 40:
        tips.append("画面对比度不足：可后期增加对比度，或选择光线更有层次的场景拍摄")
    if ae.color_harmony < 40:
        tips.append("色彩搭配不够和谐：注意画面中互补色/类似色的运用，避免杂乱色彩")

    if len(tips) <= 1:
        tips.append("各项指标表现良好，继续保持！")

    return "\n".join(tips)
