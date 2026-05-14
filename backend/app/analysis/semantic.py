"""Semantic analysis: scene classification, mood, duplicate detection, tags.

Optimized: accepts pre-computed intermediates (1MP gray/HSV) to eliminate
redundant color conversions and full-res PIL creation for hashing.
"""

import cv2
import numpy as np
from PIL import Image

try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


SCENE_LABELS = [
    "landscape", "portrait", "architecture", "night", "macro",
    "street", "indoor", "sunset", "forest", "water",
]

# Haar cascade face detector (lazy-loaded, thread-safe via GIL)
_FACE_CASCADE = None
_CASCADE_LOAD_ATTEMPTED = False


def detect_faces(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Detect faces using OpenCV Haar cascade. Returns list of (x, y, w, h)."""
    global _FACE_CASCADE, _CASCADE_LOAD_ATTEMPTED
    if _FACE_CASCADE is None and not _CASCADE_LOAD_ATTEMPTED:
        _CASCADE_LOAD_ATTEMPTED = True
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            _FACE_CASCADE = cv2.CascadeClassifier(cascade_path)
            if _FACE_CASCADE.empty():
                # Fallback: look in bundled cv2/data directory
                import sys, pathlib
                if getattr(sys, 'frozen', False):
                    bundled = pathlib.Path(sys._MEIPASS) / "cv2" / "data" / "haarcascade_frontalface_default.xml"
                    if bundled.exists():
                        _FACE_CASCADE = cv2.CascadeClassifier(str(bundled))
                if _FACE_CASCADE is None or _FACE_CASCADE.empty():
                    _FACE_CASCADE = None
        except Exception:
            _FACE_CASCADE = None
    if _FACE_CASCADE is None:
        return []
    try:
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces] if len(faces) > 0 else []
    except cv2.error:
        return []


def _classify_scene_multi(hsv: np.ndarray, gray: np.ndarray, faces: list = None) -> list[tuple[str, float]]:
    """Multi-label scene classification with confidence scores.
    Returns [(scene, confidence), ...] sorted by confidence descending, max 3 entries.
    """
    faces = faces or []
    h, w = gray.shape
    avg_brightness = gray.mean() / 255.0
    avg_saturation = hsv[:, :, 1].mean() / 255.0
    hue_mean = hsv[:, :, 0].mean()

    scores: dict[str, float] = {}

    # Night: very dark
    if avg_brightness < 0.3:
        scores["night"] = min(1.0, max(0.0, (0.3 - avg_brightness) / 0.15))

    # Sunset: warm hues, moderate brightness, decent saturation
    sunset_conf = 0.0
    if 5 < hue_mean < 25:
        sunset_conf += 0.4
    if avg_saturation > 0.3:
        sunset_conf += 0.3
    if 0.3 < avg_brightness < 0.7:
        sunset_conf += 0.3
    if sunset_conf > 0.3:
        scores["sunset"] = min(1.0, sunset_conf)

    # Water: blue-dominant, landscape aspect
    blue_pixels = cv2.inRange(hsv, (100, 30, 30), (130, 255, 255))
    blue_ratio = blue_pixels.mean() / 255.0
    water_conf = 0.0
    if blue_ratio > 0.1:
        water_conf += min(1.0, blue_ratio / 0.3) * 0.6
    if w > h:
        water_conf += 0.2
    if avg_saturation > 0.2:
        water_conf += 0.2
    if water_conf > 0.3:
        scores["water"] = min(1.0, water_conf)

    # Portrait: faces OR tall aspect with skin tones
    portrait_conf = 0.0
    if faces:
        portrait_conf = min(1.0, 0.5 + len(faces) * 0.15)
    if h > w * 1.1:
        skin_mask = cv2.inRange(hsv, (0, 30, 80), (25, 170, 255))
        skin_ratio = skin_mask.mean() / 255.0
        portrait_conf = max(portrait_conf, skin_ratio * 2.0)
    if portrait_conf > 0.3:
        scores["portrait"] = min(1.0, portrait_conf)

    # Forest: green-dominant
    green_pixels = cv2.inRange(hsv, (35, 30, 30), (85, 255, 255))
    green_ratio = green_pixels.mean() / 255.0
    if green_ratio > 0.1:
        scores["forest"] = min(1.0, green_ratio / 0.3 * 0.8 + (0.2 if w > h else 0.0))

    # Landscape: wide aspect, moderate saturation, no strong other signal
    if w > h * 1.2:
        landscape_conf = 0.4
        if 0.1 < avg_saturation < 0.6:
            landscape_conf += 0.3
        if avg_brightness > 0.2:
            landscape_conf += 0.2
        # Downweight if forest/water already strong
        if scores.get("forest", 0) < 0.4 and scores.get("water", 0) < 0.4:
            landscape_conf += 0.1
        scores["landscape"] = min(1.0, landscape_conf)

    # Architecture: tall or square, high edge density
    if h > w * 0.9:
        edge_density = cv2.Canny(gray, 50, 150).mean() / 255.0
        arch_conf = 0.0
        if h > w * 1.1 and not faces:
            arch_conf += 0.4
        if edge_density > 0.05:
            arch_conf += 0.3
        if avg_brightness > 0.2:
            arch_conf += 0.2
        if arch_conf > 0.3:
            scores["architecture"] = min(1.0, arch_conf)

    # Macro: near-square, high detail
    aspect = w / h if h > 0 else 1.0
    if 0.85 <= aspect <= 1.3:
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        macro_conf = 0.0
        if lap_var > 100:
            macro_conf += min(1.0, lap_var / 500) * 0.5
        if avg_saturation > 0.25:
            macro_conf += 0.3
        if macro_conf > 0.3:
            scores["macro"] = min(1.0, macro_conf)

    # Street: moderate brightness, low saturation, medium contrast
    street_conf = 0.0
    if 0.25 < avg_brightness < 0.75:
        street_conf += 0.3
    if avg_saturation < 0.4:
        street_conf += 0.3
    contrast = gray.std() / 128.0
    if 0.2 < contrast < 0.7:
        street_conf += 0.2
    if street_conf > 0.3:
        scores["street"] = min(1.0, street_conf)

    # Indoor: fallback with some positive signals
    indoor_conf = 0.0
    if avg_brightness < 0.5:
        indoor_conf += 0.2
    if avg_saturation < 0.4:
        indoor_conf += 0.2
    if 0.8 <= aspect <= 1.3:
        indoor_conf += 0.2
    scores["indoor"] = max(0.3, indoor_conf)  # always available as fallback

    # Sort by confidence, return top 3 with conf > 0.3
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    result = [(s, round(c, 3)) for s, c in ranked if c > 0.3][:3]
    return result if result else [("indoor", 0.5)]


def analyze_mood(hsv: np.ndarray) -> str:
    """Analyze overall mood/atmosphere from pre-computed HSV (1MP)."""
    brightness = hsv[:, :, 2].mean() / 255.0
    saturation = hsv[:, :, 1].mean() / 255.0
    hue = hsv[:, :, 0].mean()

    if brightness < 0.3:
        return "moody"
    if brightness > 0.75 and saturation < 0.3:
        return "airy"
    if hue < 15 or hue > 160:
        return "warm"
    if 85 < hue < 130:
        return "cool"
    if saturation > 0.5 and brightness > 0.5:
        return "vibrant"
    return "neutral"


def compute_image_hash(inter) -> str:
    """Compute perceptual hash from 1MP image (phash internally resizes to 8x8)."""
    if not HAS_IMAGEHASH:
        return ""
    pil_img = Image.fromarray(cv2.cvtColor(inter.bgr_1mp, cv2.COLOR_BGR2RGB))
    h = imagehash.phash(pil_img)
    return str(h)


def generate_tags(gray: np.ndarray, hsv: np.ndarray, scene: str, mood: str) -> list[str]:
    """Generate descriptive tags from pre-computed gray/HSV (1MP)."""
    tags = [scene, mood]

    brightness = gray.mean() / 255.0
    if brightness < 0.25:
        tags.append("dark")
    elif brightness > 0.75:
        tags.append("bright")

    sat = hsv[:, :, 1].mean() / 255.0
    if sat > 0.6:
        tags.append("colorful")
    elif sat < 0.15:
        tags.append("muted")

    h, w = gray.shape
    if h > w * 1.3:
        tags.append("vertical")
    elif w > h * 1.3:
        tags.append("horizontal")
    else:
        tags.append("square")

    return list(set(tags))


def compute_semantic_score(inter) -> dict:
    """Run semantic analysis using pre-computed intermediates."""
    faces = detect_faces(inter.gray_1mp)
    scene_labels = _classify_scene_multi(inter.hsv_1mp, inter.gray_1mp, faces)
    scene = scene_labels[0][0]  # primary scene for display
    mood = analyze_mood(inter.hsv_1mp)
    tags = generate_tags(inter.gray_1mp, inter.hsv_1mp, scene, mood)

    # Base scene interest score — weighted by scene confidences
    base_scores = {
        "sunset": 75, "landscape": 70, "forest": 68, "water": 66,
        "architecture": 62, "street": 60, "night": 58, "portrait": 65,
        "macro": 64, "indoor": 50,
    }
    total_conf = sum(c for _, c in scene_labels)
    base = sum(base_scores.get(s, 55) * c for s, c in scene_labels) / total_conf

    # Modulate by actual image properties (reuse already-computed values)
    brightness = inter.gray_1mp.mean() / 255.0
    saturation = inter.hsv_1mp[:, :, 1].mean() / 255.0

    modulation = 0.0
    if 0.25 < brightness < 0.75:
        modulation += 10.0
    if 0.2 < saturation < 0.6:
        modulation += 10.0
    contrast = inter.gray.std() / 128.0
    if 0.3 < contrast < 0.8:
        modulation += 10.0
    # Portrait with confirmed faces gets a bonus
    if scene == "portrait" and faces:
        modulation += 5.0
    overall = min(100.0, base + modulation)

    return {
        "scene": scene,
        "mood": mood,
        "tags": tags,
        "overall": round(float(overall), 2),
        "faces": faces,
        "scene_labels": scene_labels,
    }
