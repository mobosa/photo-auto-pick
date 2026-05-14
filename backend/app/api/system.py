"""System API: history, delete, folder browser, cache management."""

import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.core.config import settings
from app.models.database import SessionLocal, get_all_tasks, get_results_by_task, delete_photo_record, PhotoRecord, reset_engine, init_db

router = APIRouter()


# ── History ──────────────────────────────────────────────────────────
@router.get("/history")
async def list_history():
    """List all past analysis tasks with summary stats."""
    db = SessionLocal()
    try:
        rows = get_all_tasks(db)
        tasks = []
        for r in rows:
            tasks.append({
                "task_id": r.task_id,
                "photo_count": r.count,
                "avg_score": round(float(r.avg_score or 0), 1),
                "created_at": str(r.created_at) if r.created_at else "",
            })
        return {"tasks": tasks}
    finally:
        db.close()


@router.delete("/history/{task_id}")
async def delete_task_history(task_id: str):
    """Delete all records (and optionally source files) for a task."""
    db = SessionLocal()
    try:
        records = get_results_by_task(db, task_id)
        count = len(records)
        for r in records:
            db.delete(r)
        db.commit()
        return {"deleted": count, "task_id": task_id}
    finally:
        db.close()


# ── Delete ───────────────────────────────────────────────────────────
class DeleteRequest(BaseModel):
    ids: list[int]
    delete_source: bool = True


@router.post("/photos/delete")
async def delete_photos(req: DeleteRequest):
    """Delete photo records and optionally their source files."""
    db = SessionLocal()
    deleted_files = []
    deleted_records = 0
    errors = []

    try:
        for photo_id in req.ids:
            record = db.query(PhotoRecord).filter(PhotoRecord.id == photo_id).first()

            if not record:
                continue

            # Delete source file if requested
            if req.delete_source:
                fpath = Path(record.filepath)
                if fpath.exists():
                    try:
                        fpath.unlink()
                        deleted_files.append(str(fpath))
                    except Exception as e:
                        errors.append(f"{fpath.name}: {e}")

            # Delete DB record
            db.delete(record)
            deleted_records += 1

        db.commit()
        return {
            "deleted_records": deleted_records,
            "deleted_files": len(deleted_files),
            "errors": errors,
        }
    finally:
        db.close()


# ── Folder Browser ───────────────────────────────────────────────────
@router.get("/browse")
async def browse_folder(path: str = Query("", description="Folder path to browse")):
    """Browse local filesystem to select a folder."""
    if not path:
        # List drives on Windows
        import string
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append({
                    "name": drive,
                    "path": drive,
                    "is_dir": True,
                })
        return {"current": "", "items": drives}

    folder = Path(path)
    if not folder.is_dir():
        return {"error": f"Not a directory: {path}", "current": path, "items": []}

    items = []
    # Add parent directory
    parent = folder.parent
    if parent != folder:
        items.append({"name": "..", "path": str(parent), "is_dir": True})

    try:
        for entry in sorted(folder.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith("."):
                continue
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
            })
    except PermissionError:
        return {"error": "Permission denied", "current": str(folder), "items": []}

    return {"current": str(folder), "items": items}


# ── Cache Management ─────────────────────────────────────────────────
@router.post("/clear-cache")
async def clear_cache():
    import logging
    log = logging.getLogger("clear_cache")
    cleared = []
    errors = []

    # Clear uploads
    if settings.upload_dir.exists():
        count = sum(1 for _ in settings.upload_dir.rglob("*") if _.is_file())
        try:
            shutil.rmtree(settings.upload_dir)
            cleared.append(f"uploads: {count} files")
        except Exception as e:
            errors.append(f"uploads: {e}")
        settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # Clear database
    if settings.results_db.exists():
        try:
            reset_engine()  # release SQLite connections before deleting
            settings.results_db.unlink()
            cleared.append("database: reset")
        except Exception as e:
            log.warning("Failed to delete database: %s", e)
            errors.append(f"database: {e}")
    else:
        # Database doesn't exist, just reset engine for a clean start
        try:
            reset_engine()
        except Exception:
            pass

    # Clean up WAL/SHM files even if main db deletion failed
    for suffix in ["-wal", "-shm"]:
        wal_path = Path(str(settings.results_db) + suffix)
        if wal_path.exists():
            try:
                wal_path.unlink()
            except Exception:
                pass

    # Recreate database tables
    try:
        settings.results_db.parent.mkdir(parents=True, exist_ok=True)
        init_db()
    except Exception as e:
        log.warning("Failed to reinitialize database: %s", e)
        errors.append(f"db init: {e}")

    if errors:
        return {"message": "Cache partially cleared", "details": cleared, "warnings": errors}
    return {"message": "Cache cleared", "details": cleared}


@router.get("/cache-info")
async def cache_info():
    info = {}
    if settings.upload_dir.exists():
        files = list(settings.upload_dir.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        total_bytes = sum(f.stat().st_size for f in files if f.is_file())
        info["uploads"] = {"files": file_count, "size_mb": round(total_bytes / 1024 / 1024, 2)}
    if settings.results_db.exists():
        info["database_mb"] = round(settings.results_db.stat().st_size / 1024 / 1024, 2)
    return info
