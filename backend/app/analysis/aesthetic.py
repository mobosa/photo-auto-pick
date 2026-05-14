"""Aesthetic scoring using NIMA deep learning model + rule-based heuristics.

Optimized: accepts pre-computed intermediates. NIMA tensor is pre-built
in pipeline.py (avoids full-res PIL allocation). Rule-based heuristics
use 1MP gray/HSV instead of full-res.
"""

import logging
import sys
import threading
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)

_NIMA_MODEL_FILE = "nima_mobilenet.onnx"
_NIMA_INPUT_SIZE = (224, 224)
_NIMA_WEIGHT = 0.80
_RULES_WEIGHT = 0.20

if getattr(sys, 'frozen', False):
    _WEIGHTS_DIR = Path(sys._MEIPASS) / "weights"
else:
    _WEIGHTS_DIR = Path(__file__).resolve().parent.parent.parent / "weights"


# ---------------------------------------------------------------------------
# Lazy NIMA ONNX session (thread-safe)
# ---------------------------------------------------------------------------

_session = None
_model_available = None
_init_lock = threading.Lock()


def _get_nima_session():
    global _session, _model_available
    if _model_available is not None:
        return _session
    with _init_lock:
        # Double-check after acquiring lock
        if _model_available is not None:
            return _session
        model_path = _WEIGHTS_DIR / _NIMA_MODEL_FILE
        if not model_path.exists():
            log.info("NIMA model not found at %s; using rule-based scoring", model_path)
            _model_available = False
            _session = None
            return None
        try:
            import onnxruntime as ort
            from app.utils.onnx_provider import get_providers
            _session = ort.InferenceSession(
                str(model_path),
                providers=get_providers(),
            )
            _model_available = True
            log.info("NIMA model loaded from %s", model_path)
        except Exception:
            log.exception("Failed to load NIMA model; falling back to rules")
            _model_available = False
            _session = None
    return _session


def _nima_score(session, input_tensor: np.ndarray) -> float:
    """Run NIMA inference, return score scaled to 0-100."""
    input_name = session.get_inputs()[0].name
    probs = session.run(None, {input_name: input_tensor})[0][0]
    mean_score = float(np.sum(probs * np.arange(1, 11)))
    return max(0.0, min(100.0, (mean_score - 1.0) / 9.0 * 100.0))


# ---------------------------------------------------------------------------
# Rule-based heuristics (0-1 range) — accept pre-computed arrays
# ---------------------------------------------------------------------------

def _contrast_score(gray: np.ndarray) -> float:
    """RMS contrast — well-contrasted images score higher."""
    rms = gray.astype(float).std()
    if 30 <= rms <= 75:
        return 1.0
    elif rms < 30:
        return rms / 30
    else:
        return max(0, 1.0 - (rms - 75) / 50)


def _color_harmony(hsv: np.ndarray) -> float:
    """Color harmony based on dominant hue relationships."""
    hue_hist = cv2.calcHist([hsv], [0], None, [36], [0, 180]).flatten()
    total = hue_hist.sum()
    if total == 0:
        return 0.5
    top3_idx = np.argsort(hue_hist)[-3:][::-1]
    top3_ratio = sum(hue_hist[i] for i in top3_idx) / total
    if 0.35 <= top3_ratio <= 0.85:
        harmony = 1.0
    elif top3_ratio < 0.35:
        harmony = top3_ratio / 0.35
    else:
        harmony = max(0, 1.0 - (top3_ratio - 0.85) / 0.15)
    return harmony


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_aesthetic_score(inter) -> dict:
    """Compute aesthetic score using pre-computed intermediates.

    NIMA uses inter.nima_tensor (pre-built 224x224 float32).
    Rule-based uses inter.hsv_1mp (contrast + color harmony only).
    """
    contrast = _contrast_score(inter.gray_1mp) * 100
    harmony = _color_harmony(inter.hsv_1mp) * 100

    rule_based = contrast * 0.45 + harmony * 0.55

    session = _get_nima_session()
    if session is not None:
        try:
            nima = _nima_score(session, inter.nima_tensor)
            overall = nima * _NIMA_WEIGHT + rule_based * _RULES_WEIGHT
            return {
                "nima_score": round(nima, 2),
                "overall": round(overall, 2),
                "method": "nima",
                "contrast": round(contrast, 2),
                "color_harmony": round(harmony, 2),
            }
        except Exception:
            log.exception("NIMA inference failed; falling back to rules")

    return {
        "nima_score": round(rule_based, 2),
        "overall": round(rule_based, 2),
        "method": "rules",
        "contrast": round(contrast, 2),
        "color_harmony": round(harmony, 2),
    }
