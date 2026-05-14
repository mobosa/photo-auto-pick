"""PhotoAutoPick entry point — launches server and opens browser automatically."""

import sys
import os
import logging

# --noconsole (pythonw.exe) sets stdout/stderr to None at C level.
# Redirect early so print() and logging don't crash.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import time
import webbrowser
import threading
from pathlib import Path

# Ensure the backend app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Log to file so errors are visible even without a console.
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "PhotoAutoPick"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    filename=str(LOG_FILE),
    filemode="a",
    force=True,
)

from app.main import app


def open_browser():
    """Open browser after a short delay to let the server start."""
    time.sleep(2.5)
    webbrowser.open("http://127.0.0.1:8000")


def make_log_config():
    """Custom uvicorn log config that writes to file, not stderr.

    This bypasses uvicorn's DefaultFormatter which calls sys.stderr.isatty()
    and crashes under --noconsole / pythonw.exe.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(LOG_FILE),
                "formatter": "default",
                "mode": "a",
            },
        },
        "loggers": {
            "uvicorn": {"level": "INFO", "handlers": ["file"], "propagate": False},
            "uvicorn.error": {"level": "INFO", "handlers": ["file"], "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["file"], "propagate": False},
        },
    }


if __name__ == "__main__":
    import uvicorn

    logger = logging.getLogger("PhotoAutoPick")
    logger.info("=" * 50)
    logger.info("  PhotoAutoPick — 照片自动筛选")
    logger.info("  正在启动，请稍候...")
    logger.info("  浏览器将自动打开 http://127.0.0.1:8000")
    logger.info("=" * 50)

    # Open browser in background
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        log_config=make_log_config(),
    )
