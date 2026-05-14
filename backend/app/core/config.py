import sys
from pathlib import Path
from pydantic_settings import BaseSettings

# 打包后：exe 所在目录用于存放用户数据（uploads、data）
#         sys._MEIPASS 用于读取打包进 exe 的资源（frontend_dist）
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent          # 用户数据目录
    BUNDLE_DIR = Path(sys._MEIPASS)                 # 打包资源目录
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    BUNDLE_DIR = BASE_DIR


class Settings(BaseSettings):
    app_name: str = "PhotoAutoPick"
    upload_dir: Path = BASE_DIR / "uploads"
    results_db: Path = BASE_DIR / "data" / "results.db"
    static_dir: Path = BUNDLE_DIR / "frontend_dist"

    # Score weights
    weight_technical: float = 0.25
    weight_composition: float = 0.25
    weight_semantic: float = 0.15
    weight_uniqueness: float = 0.15

    class Config:
        env_prefix = "PAP_"


settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.results_db.parent.mkdir(parents=True, exist_ok=True)
