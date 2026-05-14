"""Task status API."""

from fastapi import APIRouter
from app.analysis.tasks import get_task_progress

router = APIRouter()


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get current task progress."""
    return get_task_progress(task_id)
