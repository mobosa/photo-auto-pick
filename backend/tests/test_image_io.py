"""Tests for image loading utilities."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.image_io import (
    SUPPORTED_EXTENSIONS,
    RAW_EXTENSIONS,
    is_image_file,
    load_image_pil,
    load_image_cv,
    load_image_gray,
    get_thumbnail_bytes,
    _is_raw,
)


class TestIsImageFile:
    def test_standard_formats(self):
        for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".heic", ".heif"]:
            assert is_image_file(f"photo{ext}")

    def test_raw_formats(self):
        for ext in [".cr2", ".nef", ".arw", ".dng", ".raf"]:
            assert is_image_file(f"photo{ext}")

    def test_non_image(self):
        assert not is_image_file("readme.txt")
        assert not is_image_file("data.csv")
        assert not is_image_file("script.py")

    def test_case_insensitive(self):
        assert is_image_file("PHOTO.JPG")
        assert is_image_file("photo.CR2")


class TestIsRaw:
    def test_raw_extensions(self):
        for ext in RAW_EXTENSIONS:
            assert _is_raw(f"file{ext}")

    def test_standard_not_raw(self):
        for ext in [".jpg", ".png", ".webp"]:
            assert not _is_raw(f"file{ext}")


class TestLoadImagePil:
    def test_load_jpg(self, tmp_path):
        img = Image.new("RGB", (50, 50), color=(128, 64, 32))
        p = tmp_path / "test.jpg"
        img.save(p)
        result = load_image_pil(p)
        assert result is not None
        assert result.mode == "RGB"
        assert result.size == (50, 50)

    def test_load_png(self, tmp_path):
        img = Image.new("RGB", (30, 40), color=(200, 100, 50))
        p = tmp_path / "test.png"
        img.save(p)
        result = load_image_pil(p)
        assert result is not None
        assert result.size == (30, 40)

    def test_nonexistent_returns_none(self):
        assert load_image_pil("/nonexistent/photo.jpg") is None


class TestLoadImageCv:
    def test_returns_bgr(self, tmp_path):
        img = Image.new("RGB", (50, 50), color=(255, 0, 0))
        p = tmp_path / "test.jpg"
        img.save(p)
        result = load_image_cv(p)
        assert result is not None
        assert len(result.shape) == 3
        assert result.shape[2] == 3
        # Red in BGR: channel 2 should be high
        assert result[0, 0, 2] > 200

    def test_nonexistent_returns_none(self):
        assert load_image_cv("/nonexistent/photo.jpg") is None


class TestLoadImageGray:
    def test_returns_grayscale(self, tmp_path):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        p = tmp_path / "test.jpg"
        img.save(p)
        result = load_image_gray(p)
        assert result is not None
        assert len(result.shape) == 2


class TestGetThumbnailBytes:
    def test_returns_jpeg_bytes(self, tmp_path):
        img = Image.new("RGB", (500, 500), color=(100, 100, 100))
        p = tmp_path / "test.jpg"
        img.save(p)
        thumb = get_thumbnail_bytes(p, size=(100, 100))
        assert thumb is not None
        assert isinstance(thumb, bytes)
        # JPEG magic bytes
        assert thumb[:2] == b'\xff\xd8'

    def test_nonexistent_returns_none(self):
        assert get_thumbnail_bytes("/nonexistent/photo.jpg") is None
