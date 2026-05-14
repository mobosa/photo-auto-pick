"""Results API: query and export analysis results."""

import json
from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import Response
from app.models.database import SessionLocal, get_results_by_task, PhotoRecord
from app.utils.image_io import get_thumbnail_bytes
from app.core.config import settings

router = APIRouter()


def _record_to_result(record) -> dict:
    return {
        "id": record.id,
        "filename": record.filename,
        "filepath": record.filepath,
        "task_id": record.task_id,
        "technical": json.loads(record.technical_json),
        "composition": json.loads(record.composition_json),
        "face_json": record.face_json or "{}",
        "semantic": json.loads(record.semantic_json),
        "aesthetic": json.loads(record.aesthetic_json) if record.aesthetic_json else {},
        "exif": json.loads(record.exif_json) if record.exif_json else {},
        "suggestions": record.suggestions or "",
        "uniqueness": record.uniqueness,
        "final_score": record.final_score,
        "grade": record.grade,
        "created_at": str(record.created_at) if record.created_at else None,
    }


@router.get("/results/{task_id}")
async def get_results(
    task_id: str,
    min_score: float = Query(0, ge=0, le=100),
    grade: str = Query("", regex="^(S|A|B\+|B|C\+|C|D)?$"),
    sort_by: str = Query("final_score", regex="^(final_score|filename)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    db = SessionLocal()
    try:
        records = get_results_by_task(db, task_id)
        results = [_record_to_result(r) for r in records]

        if min_score > 0:
            results = [r for r in results if r["final_score"] >= min_score]
        if grade:
            results = [r for r in results if r["grade"] == grade]

        reverse = sort_by == "final_score"
        results.sort(key=lambda r: r[sort_by], reverse=reverse)

        total = len(results)
        page = results[offset:offset + limit]

        return {
            "task_id": task_id,
            "count": total,
            "offset": offset,
            "limit": limit,
            "results": page,
        }
    finally:
        db.close()


@router.get("/results/{task_id}/export")
async def export_good_photos(task_id: str, min_score: float = Query(70)):
    db = SessionLocal()
    try:
        records = get_results_by_task(db, task_id)
        good = [r.filepath for r in records if r.final_score >= min_score]
        return {"task_id": task_id, "count": len(good), "file_paths": good}
    finally:
        db.close()


@router.get("/thumbnail/{task_id}/{filename}")
async def get_thumbnail(task_id: str, filename: str):
    """Serve a JPEG thumbnail for the given photo."""
    # First try upload directory (for uploaded files)
    filepath = settings.upload_dir / task_id / filename
    if not filepath.exists():
        # Fallback: look up actual path in database (for folder-scanned files)
        db = SessionLocal()
        try:
            from sqlalchemy import and_
            record = db.query(PhotoRecord).filter(
                and_(PhotoRecord.task_id == task_id, PhotoRecord.filename == filename)
            ).first()
            if record and Path(record.filepath).exists():
                filepath = Path(record.filepath)
            else:
                return Response(content=b"File not found", status_code=404)
        finally:
            db.close()
    thumb = get_thumbnail_bytes(filepath, size=(400, 400))
    if thumb is None:
        return Response(content=b"Cannot generate thumbnail", status_code=500)
    return Response(
        content=thumb,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
