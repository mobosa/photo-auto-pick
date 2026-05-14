import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, func, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

def _make_engine():
    eng = create_engine(
        f"sqlite:///{settings.results_db}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    # Enable WAL mode for better concurrent read/write support
    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
    return eng

engine = _make_engine()
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class PhotoRecord(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    task_id = Column(String, index=True, nullable=False)
    technical_json = Column(Text, default="{}")
    composition_json = Column(Text, default="{}")
    face_json = Column(Text, default="{}")
    semantic_json = Column(Text, default="{}")
    aesthetic_json = Column(Text, default="{}")
    exif_json = Column(Text, default="{}")
    suggestions = Column(Text, default="")
    uniqueness = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    grade = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)
    # Add exif_json column to existing databases that predate this field
    with engine.connect() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(photos)").fetchall()]
        if "exif_json" not in cols:
            conn.exec_driver_sql("ALTER TABLE photos ADD COLUMN exif_json TEXT DEFAULT '{}'")


def reset_engine():
    """Dispose the current engine and recreate it (call before deleting DB file)."""
    global engine, SessionLocal
    engine.dispose()
    engine = _make_engine()
    SessionLocal.configure(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_photo_result(db, result):
    record = PhotoRecord(
        filename=result.filename,
        filepath=result.filepath,
        task_id=result.task_id,
        technical_json=result.technical.model_dump_json(),
        composition_json=result.composition.model_dump_json(),
        face_json=result.face_json,
        semantic_json=result.semantic.model_dump_json(),
        aesthetic_json=result.aesthetic.model_dump_json(),
        exif_json=result.exif.model_dump_json(),
        suggestions=result.suggestions,
        uniqueness=result.uniqueness,
        final_score=result.final_score,
        grade=result.grade,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def save_photo_results_batch(db, results: list) -> list:
    """Batch-insert photo results with a single commit for the entire batch."""
    records = []
    for result in results:
        record = PhotoRecord(
            filename=result.filename,
            filepath=result.filepath,
            task_id=result.task_id,
            technical_json=result.technical.model_dump_json(),
            composition_json=result.composition.model_dump_json(),
            face_json=result.face_json,
            semantic_json=result.semantic.model_dump_json(),
            aesthetic_json=result.aesthetic.model_dump_json(),
            exif_json=result.exif.model_dump_json(),
            suggestions=result.suggestions,
            uniqueness=result.uniqueness,
            final_score=result.final_score,
            grade=result.grade,
        )
        db.add(record)
        records.append(record)
    db.commit()
    for r in records:
        db.refresh(r)
    return records


def get_results_by_task(db, task_id: str):
    return db.query(PhotoRecord).filter(PhotoRecord.task_id == task_id).all()


def get_all_tasks(db):
    """Return summary of all tasks: task_id, count, avg_score, date, folder."""
    rows = (
        db.query(
            PhotoRecord.task_id,
            func.count(PhotoRecord.id).label("count"),
            func.avg(PhotoRecord.final_score).label("avg_score"),
            func.min(PhotoRecord.created_at).label("created_at"),
        )
        .group_by(PhotoRecord.task_id)
        .order_by(func.min(PhotoRecord.created_at).desc())
        .all()
    )
    return rows


def delete_photo_record(db, photo_id: int):
    record = db.query(PhotoRecord).filter(PhotoRecord.id == photo_id).first()
    if record:
        db.delete(record)
        db.commit()
    return record
