import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps

# Register HEIF/HEIC support (no-op if pillow-heif not installed)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

# Register RAW support (no-op if rawpy not installed)
try:
    import rawpy
except ImportError:
    rawpy = None

RAW_EXTENSIONS = {".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2", ".dng", ".pef", ".srw", ".3fr", ".kdc", ".mrw"}
STANDARD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".heic", ".heif"}
SUPPORTED_EXTENSIONS = STANDARD_EXTENSIONS | RAW_EXTENSIONS


def is_image_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def _apply_exif_orientation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation so the image displays upright."""
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def _is_raw(path: str | Path) -> bool:
    return Path(path).suffix.lower() in RAW_EXTENSIONS


def _load_raw_rgb(path: str | Path) -> Image.Image | None:
    """Decode a RAW file to RGB PIL Image via rawpy."""
    if rawpy is None:
        return None
    try:
        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess(use_camera_wb=True, half_size=False, no_auto_bright=True)
        return Image.fromarray(rgb)
    except Exception:
        return None


def load_image_pil(path: str | Path) -> Image.Image | None:
    """Load image as RGB PIL Image, corrected for EXIF orientation."""
    try:
        if _is_raw(path):
            return _load_raw_rgb(path)
        img = Image.open(path)
        img = _apply_exif_orientation(img)
        return img.convert("RGB")
    except Exception:
        return None


def load_image_cv(path: str | Path) -> np.ndarray | None:
    """Load image as BGR numpy array, corrected for EXIF orientation."""
    try:
        if _is_raw(path):
            pil_img = _load_raw_rgb(path)
            if pil_img is None:
                return None
            arr = np.array(pil_img)
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        pil_img = Image.open(path)
        pil_img = _apply_exif_orientation(pil_img)
        rgb = pil_img.convert("RGB")
        arr = np.array(rgb)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return bgr
    except Exception:
        return None


def load_image_gray(path: str | Path) -> np.ndarray | None:
    """Load image as grayscale numpy array, corrected for EXIF orientation."""
    if _is_raw(path):
        pil_img = _load_raw_rgb(path)
        if pil_img is None:
            return None
        return np.array(pil_img.convert("L"))
    pil_img = Image.open(path)
    pil_img = _apply_exif_orientation(pil_img)
    gray = pil_img.convert("L")
    return np.array(gray)


def get_thumbnail_bytes(path: str | Path, size: tuple = (200, 200)) -> bytes | None:
    """Generate JPEG thumbnail bytes for preview, correctly oriented."""
    img = load_image_pil(path)
    if img is None:
        return None
    img.thumbnail(size, Image.LANCZOS)
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def extract_exif(filepath: str | Path) -> dict:
    """Extract camera/lens/settings EXIF metadata from an image file."""
    try:
        p = Path(filepath)
        if _is_raw(p):
            return _extract_exif_raw(p)
        return _extract_exif_pil(p)
    except Exception:
        return {}


_METERING_MODES = {
    "1": "平均测光", "2": "中央重点", "3": "点测光",
    "4": "多点测光", "5": "矩阵测光", "6": "局部测光",
}

_EXPOSURE_PROGRAMS = {
    "0": "未定义", "1": "手动M", "2": "程序自动P",
    "3": "光圈优先A", "4": "快门优先S", "5": "创意模式",
    "6": "运动模式", "7": "肖像模式", "8": "风景模式",
}

_WB_MAP = {
    "0": "自动", "1": "手动",
    "Auto": "自动", "Manual": "手动",
}


def _extract_exif_pil(p: Path) -> dict:
    """Extract EXIF from standard formats using Pillow."""
    from PIL.ExifTags import TAGS

    img = Image.open(p)
    exif_data = img.getexif()
    if not exif_data:
        return {}

    tags = {}
    for tag_id, value in exif_data.items():
        name = TAGS.get(tag_id, tag_id)
        tags[name] = value

    # Image size
    w = tags.get("ExifImageWidth") or tags.get("ImageWidth") or img.width
    h = tags.get("ExifImageLength") or tags.get("ImageLength") or img.height

    # Metering mode
    metering = str(tags.get("MeteringMode", ""))
    metering_str = _METERING_MODES.get(metering, metering)

    # Exposure program
    eprog = str(tags.get("ExposureProgram", ""))
    eprog_str = _EXPOSURE_PROGRAMS.get(eprog, eprog)

    # White balance
    wb = str(tags.get("WhiteBalance", ""))
    wb_str = _WB_MAP.get(wb, wb)

    # Exposure compensation
    ev = tags.get("ExposureBiasValue")
    ev_str = _format_ev(ev)

    # Flash
    flash_val = tags.get("Flash")
    flash_str = _format_flash(flash_val)

    # Color space
    cs = tags.get("ColorSpace")
    cs_str = "Adobe RGB" if cs == 0xFFFF else ("sRGB" if cs == 1 else str(cs) if cs else "")

    # Focal length in 35mm
    fl35 = tags.get("FocalLengthIn35mmFilm")
    fl35_str = f"{fl35}mm" if fl35 else ""

    info = {
        "camera_make": str(tags.get("Make", "")).strip(),
        "camera_model": str(tags.get("Model", "")).strip(),
        "lens_model": str(tags.get("LensModel", "")).strip(),
        "focal_length": _format_focal_length(tags.get("FocalLength")),
        "focal_length_35mm": fl35_str,
        "aperture": _format_aperture(tags.get("FNumber") or tags.get("ApertureValue")),
        "iso": str(tags.get("ISOSpeedRatings", "")),
        "shutter_speed": _format_shutter(tags.get("ExposureTime")),
        "exposure_comp": ev_str,
        "exposure_program": eprog_str,
        "white_balance": wb_str,
        "metering_mode": metering_str,
        "flash": flash_str,
        "image_size": f"{w}x{h}",
        "color_space": cs_str,
        "datetime_original": str(tags.get("DateTimeOriginal", "")).strip(),
    }
    return info


def _extract_exif_raw(p: Path) -> dict:
    """Extract EXIF from RAW files using exifread."""
    try:
        import exifread
    except ImportError:
        return {}

    with open(p, "rb") as f:
        tags = exifread.process_file(f, details=False)

    def _get(key: str) -> str:
        return str(tags.get(key, "")).strip()

    # Image size
    iw = _get("EXIF ExifImageWidth") or _get("Image ImageWidth")
    ih = _get("EXIF ExifImageLength") or _get("Image ImageLength")
    size_str = f"{iw}x{ih}" if iw and ih else ""

    # Metering mode
    metering = _get("EXIF MeteringMode")
    metering_str = _METERING_MODES.get(metering, metering)

    # Exposure program
    eprog = _get("EXIF ExposureProgram")
    eprog_str = _EXPOSURE_PROGRAMS.get(eprog, eprog)

    # White balance
    wb = _get("EXIF WhiteBalance")
    ct = _get("MakerNote ColorTemperature")
    wb_str = _WB_MAP.get(wb, wb)
    if ct and ct.isdigit():
        wb_str = f"{wb_str} {ct}K" if wb_str else f"{ct}K"

    # Exposure compensation
    ev_str = _format_ev_raw(_get("EXIF ExposureBiasValue"))

    # Flash
    flash_str = _format_flash_raw(_get("EXIF Flash"))

    # Color space
    cs = _get("EXIF ColorSpace")
    cs_str = "Adobe RGB" if "uncalibrated" in cs.lower() or cs == "65535" else ("sRGB" if cs == "1" else cs)

    # Focal length in 35mm
    fl35 = _get("EXIF FocalLengthIn35mmFilm")
    fl35_str = f"{fl35}mm" if fl35 else ""

    aperture = _get("EXIF FNumber")
    if not aperture:
        aperture = _get("EXIF ApertureValue")

    info = {
        "camera_make": _get("Image Make"),
        "camera_model": _get("Image Model"),
        "lens_model": _get("EXIF LensModel") or _get("EXIF LensInfo"),
        "focal_length": _get("EXIF FocalLength"),
        "focal_length_35mm": fl35_str,
        "aperture": aperture,
        "iso": _get("EXIF ISOSpeedRatings"),
        "shutter_speed": _get("EXIF ExposureTime"),
        "exposure_comp": ev_str,
        "exposure_program": eprog_str,
        "white_balance": wb_str,
        "metering_mode": metering_str,
        "flash": flash_str,
        "image_size": size_str,
        "color_space": cs_str,
        "datetime_original": _get("EXIF DateTimeOriginal"),
    }
    return info


def _format_ev(val) -> str:
    if val is None:
        return ""
    try:
        if hasattr(val, "numerator"):
            v = float(val.numerator) / float(val.denominator)
        else:
            v = float(val)
        if v == 0:
            return "0 EV"
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.1f} EV"
    except (ValueError, ZeroDivisionError):
        return str(val)


def _format_ev_raw(val: str) -> str:
    if not val:
        return ""
    try:
        # exifread returns strings like "0" or "+1.3" or "-0.7"
        v = float(val)
        if v == 0:
            return "0 EV"
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.1f} EV"
    except ValueError:
        return val


def _format_flash(val) -> str:
    if val is None:
        return ""
    fired = bool(val & 1) if isinstance(val, int) else False
    return "已闪光" if fired else "未闪光"


def _format_flash_raw(val: str) -> str:
    if not val:
        return ""
    try:
        v = int(val)
        fired = bool(v & 1)
        return "已闪光" if fired else "未闪光"
    except ValueError:
        return val


def _format_focal_length(val) -> str:
    if val is None:
        return ""
    try:
        if hasattr(val, "numerator"):
            return f"{float(val.numerator) / float(val.denominator):.0f}mm"
        return f"{float(val):.0f}mm"
    except (ValueError, ZeroDivisionError):
        return str(val)


def _format_aperture(val) -> str:
    if val is None:
        return ""
    try:
        if hasattr(val, "numerator"):
            v = float(val.numerator) / float(val.denominator)
        else:
            v = float(val)
        return f"f/{v:.1f}"
    except (ValueError, ZeroDivisionError):
        return str(val)


def _format_shutter(val) -> str:
    if val is None:
        return ""
    try:
        if hasattr(val, "numerator"):
            v = float(val.numerator) / float(val.denominator)
        else:
            v = float(val)
        if v < 1:
            return f"1/{int(1 / v)}s"
        return f"{v:.1f}s"
    except (ValueError, ZeroDivisionError):
        return str(val)
