"""Shared ONNX Runtime provider selection with GPU fallback."""

import logging

import onnxruntime

log = logging.getLogger(__name__)


def get_providers() -> list[str]:
    """Return ONNX Runtime providers, preferring GPU when available."""
    try:
        available = set(onnxruntime.get_available_providers())
    except Exception:
        return ["CPUExecutionProvider"]

    if "CUDAExecutionProvider" in available:
        log.info("Using CUDAExecutionProvider for ONNX inference")
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]

    if "DmlExecutionProvider" in available:
        log.info("Using DmlExecutionProvider for ONNX inference")
        return ["DmlExecutionProvider", "CPUExecutionProvider"]

    return ["CPUExecutionProvider"]
