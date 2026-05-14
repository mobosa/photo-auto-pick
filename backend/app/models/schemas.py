from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TechnicalScores(BaseModel):
    exposure: float = 0.0
    color: float = 0.0
    sharpness: float = 0.0
    noise: float = 0.0
    dynamic_range: float = 0.0
    focus_quality: float = 0.0
    color_richness: float = 0.0
    overall: float = 0.0


class CompositionScores(BaseModel):
    rule_of_thirds: float = 0.0
    symmetry: float = 0.0
    horizon_level: float = 0.0
    negative_space: float = 0.0
    leading_lines: float = 0.0
    depth_of_field: float = 0.0
    overall: float = 0.0


class SemanticScores(BaseModel):
    scene: str = ""
    mood: str = ""
    tags: list[str] = []
    overall: float = 0.0


class AestheticScores(BaseModel):
    nima_score: float = 0.0
    overall: float = 0.0
    method: str = "rules"
    contrast: float = 0.0
    color_harmony: float = 0.0


class ExifInfo(BaseModel):
    camera_make: str = ""
    camera_model: str = ""
    lens_model: str = ""
    focal_length: str = ""
    focal_length_35mm: str = ""
    aperture: str = ""
    iso: str = ""
    shutter_speed: str = ""
    exposure_comp: str = ""
    exposure_program: str = ""
    white_balance: str = ""
    metering_mode: str = ""
    flash: str = ""
    image_size: str = ""
    color_space: str = ""
    datetime_original: str = ""


class PhotoResult(BaseModel):
    id: Optional[int] = None
    filename: str
    filepath: str
    task_id: str
    technical: TechnicalScores = TechnicalScores()
    composition: CompositionScores = CompositionScores()
    semantic: SemanticScores = SemanticScores()
    aesthetic: AestheticScores = AestheticScores()
    exif: ExifInfo = ExifInfo()
    face_json: str = "{}"
    suggestions: str = ""
    uniqueness: float = 0.0
    final_score: float = 0.0
    grade: str = ""
    created_at: Optional[datetime] = None


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    total: int = 0
    processed: int = 0
    current_file: str = ""
    error: str = ""
