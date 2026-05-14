"""Tests for the aesthetic scoring module."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.aesthetic import (
    _contrast_score,
    _color_harmony,
    _composition_balance,
    _brightness_appeal,
    _color_diversity,
    compute_aesthetic_score,
)
from app.analysis.pipeline import build_intermediates


def _make_image(width=200, height=200, color=(128, 128, 128)):
    """Create a simple BGR test image."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    return img


def _make_gradient():
    """Create a gradient image with varying brightness."""
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    for i in range(200):
        img[i, :, :] = int(i * 255 / 200)
    return img


def _gray(bgr):
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def _hsv(bgr):
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)


class TestContrastScore:
    def test_uniform_low_contrast(self):
        img = _make_image(color=(128, 128, 128))
        assert _contrast_score(_gray(img)) < 0.1

    def test_gradient_has_contrast(self):
        img = _make_gradient()
        assert _contrast_score(_gray(img)) > 0.5

    def test_range(self):
        for _ in range(5):
            img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
            score = _contrast_score(_gray(img))
            assert 0.0 <= score <= 1.0


class TestColorHarmony:
    def test_monochrome(self):
        img = _make_image(color=(200, 200, 200))
        assert _color_harmony(_hsv(img)) == 0.5

    def test_single_hue(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :, 2] = 255  # pure red in BGR
        score = _color_harmony(_hsv(img))
        assert 0.0 <= score <= 1.0

    def test_range(self):
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        score = _color_harmony(_hsv(img))
        assert 0.0 <= score <= 1.0


class TestCompositionBalance:
    def test_symmetric(self):
        img = _make_image(color=(100, 100, 100))
        assert _composition_balance(_gray(img)) > 0.99

    def test_imbalanced(self):
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[:100, :100, :] = 255  # top-left bright, rest dark
        score = _composition_balance(_gray(img))
        assert score < 0.9


class TestBrightnessAppeal:
    def test_mid_brightness(self):
        img = _make_image(color=(128, 128, 128))
        assert _brightness_appeal(_gray(img)) == 1.0

    def test_too_dark(self):
        img = _make_image(color=(10, 10, 10))
        assert _brightness_appeal(_gray(img)) < 0.5

    def test_too_bright(self):
        img = _make_image(color=(250, 250, 250))
        assert _brightness_appeal(_gray(img)) < 0.5


class TestColorDiversity:
    def test_monochrome_low(self):
        img = _make_image(color=(128, 128, 128))
        assert _color_diversity(_hsv(img)) == 0.5

    def test_colorful(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :20, 2] = 255
        img[:, 20:40, 1] = 255
        img[:, 40:60, 0] = 255
        img[:, 60:80, :] = [255, 255, 0]
        img[:, 80:, :] = [0, 255, 255]
        score = _color_diversity(_hsv(img))
        assert score > 0.3


class TestComputeAestheticScore:
    def test_returns_required_keys(self):
        inter = build_intermediates(_make_image())
        result = compute_aesthetic_score(inter)
        assert "nima_score" in result
        assert "overall" in result
        assert "method" in result
        assert "contrast" in result
        assert "color_harmony" in result
        assert "composition_balance" in result
        assert "brightness" in result
        assert "color_diversity" in result

    def test_method_is_rules_when_no_model(self):
        inter = build_intermediates(_make_image())
        result = compute_aesthetic_score(inter)
        assert result["method"] in ("rules", "nima")

    def test_scores_in_range(self):
        inter = build_intermediates(_make_image())
        result = compute_aesthetic_score(inter)
        for key in ["nima_score", "overall", "contrast", "color_harmony",
                     "composition_balance", "brightness", "color_diversity"]:
            assert 0.0 <= result[key] <= 100.0, f"{key}={result[key]} out of range"

    def test_good_photo_scores_higher_than_bad(self):
        good = build_intermediates(_make_gradient())
        bad = build_intermediates(_make_image(color=(5, 5, 5)))
        good_score = compute_aesthetic_score(good)["overall"]
        bad_score = compute_aesthetic_score(bad)["overall"]
        assert good_score > bad_score
