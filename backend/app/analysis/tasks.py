"""Async photo analysis using thread pool (no Celery dependency).

Optimized for 1000+ images: batch DB writes, increased worker count,
NIMA session warm-up.
"""

import os
import uuid
import logging
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger("photo_analysis")

# In-memory task progress tracking
_task_progress: dict[str, dict] = {}
_lock = threading.Lock()

_POOL = None
_BATCH_SIZE = 50


def _get_pool() -> ThreadPoolExecutor:
    global _POOL
    if _POOL is None:
        workers = min(os.cpu_count() or 4, 8)
        _POOL = ThreadPoolExecutor(max_workers=workers)
        log.info("Thread pool created with %d workers", workers)
    return _POOL


def get_task_progress(task_id: str) -> dict:
    with _lock:
        return _task_progress.get(task_id, {
            "task_id": task_id,
            "status": "unknown",
            "total": 0,
            "processed": 0,
            "current_file": "",
        })


def update_progress(task_id: str, **kwargs):
    with _lock:
        if task_id not in _task_progress:
            _task_progress[task_id] = {
                "task_id": task_id, "status": "pending",
                "total": 0, "processed": 0, "current_file": "",
            }
        _task_progress[task_id].update(kwargs)


def _run_analysis(task_id: str, file_paths: list[str]):
    """Run the full analysis pipeline in a background thread."""
    total = len(file_paths)
    log.info("Task %s started: %d photos", task_id, total)
    update_progress(task_id, status="processing", total=total, processed=0)

    try:
        from app.models.database import SessionLocal, save_photo_results_batch
        from app.models.schemas import PhotoResult
        from app.analysis.pipeline import analyze_single_photo, compute_final_score, generate_suggestions, compute_uniqueness

        # Warm up NIMA ONNX session before parallel work
        try:
            from app.analysis.aesthetic import _get_nima_session
            _get_nima_session()
        except Exception:
            pass

        pool = _get_pool()
        future_to_path = {
            pool.submit(analyze_single_photo, fpath, task_id): fpath
            for fpath in file_paths
        }

        results: list[PhotoResult] = []
        hashes: dict[str, str] = {}

        for i, future in enumerate(as_completed(future_to_path)):
            fpath = future_to_path[future]
            try:
                result, phash = future.result()
                if phash:
                    hashes[fpath] = phash
                results.append(result)
            except Exception as e:
                log.warning("Task %s: failed to analyze %s: %s", task_id, fpath, e)

            update_progress(
                task_id,
                current_file=Path(fpath).name,
                processed=i + 1,
            )

        # Compute pHash-based uniqueness for all photos
        compute_uniqueness(results, hashes)

        # Recalculate final scores now that uniqueness is real
        for r in results:
            compute_final_score(r)
            r.suggestions = generate_suggestions(r)

        # Duplicate detection (exact hash collisions get extreme uniqueness overrides)
        from collections import defaultdict
        hash_groups: dict[str, list[int]] = defaultdict(list)
        for idx, r in enumerate(results):
            h = hashes.get(r.filepath, "")
            if h:
                hash_groups[h].append(idx)

        dup_count = 0
        for h, indices in hash_groups.items():
            if len(indices) > 1:
                sorted_idx = sorted(indices, key=lambda i: results[i].final_score, reverse=True)
                results[sorted_idx[0]].uniqueness = 100.0
                for idx in sorted_idx[1:]:
                    results[idx].uniqueness = 30.0
                    results[idx] = compute_final_score(results[idx])
                    results[idx].suggestions = generate_suggestions(results[idx])
                    dup_count += 1

        # Batch DB writes (50 per commit instead of 1 per commit)
        saved_count = 0
        db = SessionLocal()
        try:
            for batch_start in range(0, len(results), _BATCH_SIZE):
                batch = results[batch_start:batch_start + _BATCH_SIZE]
                save_photo_results_batch(db, batch)
                saved_count += len(batch)
        except Exception:
            log.exception("Task %s: DB write failed after saving %d/%d photos",
                          task_id, saved_count, len(results))
            raise
        finally:
            db.close()

        log.info("Task %s completed: %d photos, %d duplicates", task_id, len(results), dup_count)
        update_progress(task_id, status="completed", processed=total)

    except Exception as e:
        log.exception("Task %s failed", task_id)
        update_progress(task_id, status="failed", current_file=f"FATAL: {e}")


def submit_batch(task_id: str, file_paths: list[str]) -> str:
    """Start analysis in a background thread using the caller-provided task_id."""
    update_progress(task_id, status="pending", total=len(file_paths))

    thread = threading.Thread(
        target=_run_analysis,
        args=(task_id, file_paths),
        daemon=True,
    )
    thread.start()
    return task_id
