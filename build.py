"""One-click build script: builds frontend then packages backend into exe."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
BACKEND_DIR = ROOT / "backend"
STATIC_DEST = BACKEND_DIR / "frontend_dist"
WEIGHTS_DIR = BACKEND_DIR / "weights"


def run(cmd, cwd):
    print(f"\n>>> {' '.join(cmd)}  (in {cwd})")
    subprocess.check_call(cmd, cwd=str(cwd), shell=(sys.platform == "win32"))


def build_frontend():
    print("\n[1/3] Building frontend...")
    if not (FRONTEND_DIR / "node_modules").exists():
        run(["npm", "install"], FRONTEND_DIR)
    # Vite config outputs directly to backend/frontend_dist (emptyOutDir: true)
    run(["npm", "run", "build"], FRONTEND_DIR)
    print(f"  Frontend built → {STATIC_DEST}")


def build_exe():
    print("\n[2/3] Packaging with PyInstaller...")

    # PyInstaller args
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--noconsole",
        "--name", "PhotoAutoPick",
        "--add-data", f"{STATIC_DEST};frontend_dist",
        "--add-data", f"{WEIGHTS_DIR};weights",
        "--hidden-import", "cv2",
        "--hidden-import", "onnxruntime",
        "--hidden-import", "imagehash",
        "--hidden-import", "pillow_heif",
        "--hidden-import", "rawpy",
        "--hidden-import", "exifread",
        "--hidden-import", "scipy",
        "--hidden-import", "scipy.spatial",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        str(BACKEND_DIR / "run.py"),
    ]
    run(args, ROOT)

    exe_path = ROOT / "dist" / "PhotoAutoPick.exe"
    if exe_path.exists():
        print(f"\n[3/3] Done! EXE at: {exe_path}")
        print(f"  Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("\n[ERROR] EXE not found after build!")
        sys.exit(1)


if __name__ == "__main__":
    build_frontend()
    build_exe()
