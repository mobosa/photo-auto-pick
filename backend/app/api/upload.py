"""Upload API: accepts photo files or a folder path, dispatches analysis."""

import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.utils.image_io import is_image_file
from app.analysis.tasks import submit_batch

router = APIRouter()

# Maximum upload size per file (50 MB)
_MAX_FILE_SIZE = 50 * 1024 * 1024


class FolderRequest(BaseModel):
    folder_path: str


def _safe_filename(name: str) -> str:
    """Strip path components to prevent traversal attacks."""
    return Path(name).name


@router.post("/upload")
async def upload_photos(files: list[UploadFile] = File(...)):
    """Upload photos and start analysis task."""
    task_id = str(uuid.uuid4())[:8]
    task_dir = settings.upload_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for f in files:
        if not is_image_file(f.filename):
            continue
        # Read with size limit
        content = await f.read()
        if len(content) > _MAX_FILE_SIZE:
            continue
        dest = task_dir / _safe_filename(f.filename)
        with open(dest, "wb") as buf:
            buf.write(content)
        saved_paths.append(str(dest))

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid image files found")

    submit_batch(task_id, saved_paths)

    return {
        "task_id": task_id,
        "file_count": len(saved_paths),
        "message": "Analysis started",
    }


@router.post("/scan-folder")
async def scan_folder(req: FolderRequest):
    """Scan a local folder for photos and start analysis (no file copy)."""
    folder = Path(req.folder_path).resolve()
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Folder not found: {req.folder_path}")

    image_paths = [
        str(p) for p in sorted(folder.iterdir())
        if p.is_file() and is_image_file(p.name)
    ]

    if not image_paths:
        raise HTTPException(status_code=400, detail="No image files found in folder")

    task_id = str(uuid.uuid4())[:8]
    submit_batch(task_id, image_paths)

    return {
        "task_id": task_id,
        "file_count": len(image_paths),
        "folder": str(folder),
        "message": "Analysis started",
    }
