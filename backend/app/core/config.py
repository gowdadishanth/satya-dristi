import os
from pathlib import Path
from typing import Any, List
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Satya Dristi"
    PROJECT_DESCRIPTOR: str = "Multimodal Earth Observation Intelligence"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(x) for x in v]
        return ["*"]
    
    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    CACHE_DIR: Path = DATA_DIR / "cache"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    REPORTS_DIR: Path = DATA_DIR / "reports"
    EVIDENCE_DIR: Path = DATA_DIR / "evidence"
    
    # Satellite STAC Endpoints
    COPERNICUS_STAC_URL: str = "https://stac.dataspace.copernicus.eu/v1"
    EARTH_SEARCH_STAC_URL: str = "https://earth-search.aws.element84.com/v1"
    
    # Firebase / Firestore
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "satya-dristi")
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    
    # AI Provider & Gemini API Configuration
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Default device & execution (legacy fallback)
    MAX_VRAM_USAGE_MB: int = 3500
    PREFER_GPU: bool = True

    # Upload limits & streaming configuration
    MAX_UPLOAD_BYTES: int = 150 * 1024 * 1024       # 150 MB max per file
    MAX_TOTAL_UPLOAD_BYTES: int = 300 * 1024 * 1024  # 300 MB max total per request
    UPLOAD_CHUNK_BYTES: int = 1024 * 1024           # 1 MB chunk stream buffer

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()

# Ensure required directories exist
for folder in [settings.DATA_DIR, settings.CACHE_DIR, settings.UPLOADS_DIR, settings.REPORTS_DIR, settings.EVIDENCE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
