"""Application settings.

Every value comes from an environment variable or from the `.env` file in the
`backend/` folder. Nothing secret is hard-coded.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The backend/ folder. Relative paths in the settings are resolved from here.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- App ----
    app_name: str = "EduGuide AI"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    # Comma-separated list of frontend addresses allowed to call this API.
    cors_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://eduguide:eduguide@localhost:5432/eduguide"
    db_echo: bool = False

    # ---- Auth ----
    jwt_secret_key: str = ""
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=14, ge=1)
    # How long a "child mode" session started by a parent stays valid.
    child_session_expire_minutes: int = Field(default=720, ge=1)

    # ---- Limits ----
    max_students_per_parent: int = Field(default=10, ge=1)

    # ---- Uploaded books ----
    # Where uploaded files are kept. Only "local" (a folder on this computer) exists today.
    storage_backend: Literal["local"] = "local"
    # Relative paths are relative to the backend/ folder. Never inside a folder the web server serves.
    storage_dir: str = "storage/uploads"
    max_upload_mb: int = Field(default=50, ge=1, le=500)
    max_pdf_pages: int = Field(default=600, ge=1)
    max_documents_per_book: int = Field(default=40, ge=1)
    max_books_per_account: int = Field(default=200, ge=1)
    # How many books are read at the same time in the background.
    processing_concurrency: int = Field(default=2, ge=1, le=16)

    # ---- Reading scanned pages (OCR) ----
    # "none": scanned pages are skipped. "tesseract": uses the free Tesseract program, which must be
    # installed separately (macOS: `brew install tesseract tesseract-lang`).
    ocr_provider: Literal["none", "tesseract"] = "none"
    tesseract_cmd: str = "tesseract"
    # Tesseract language codes joined with "+". hin = Hindi, eng = English.
    ocr_languages: str = "eng+hin"

    @field_validator("jwt_secret_key")
    @classmethod
    def _secret_must_be_strong(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError(
                "JWT_SECRET_KEY is missing or shorter than 32 characters. "
                "Run `python -m scripts.init_env` inside backend/ to create a .env with a random secret."
            )
        return value

    @model_validator(mode="after")
    def _production_must_be_locked_down(self) -> "Settings":
        if self.environment == "production":
            if "*" in self.cors_origin_list:
                raise ValueError("CORS_ORIGINS cannot contain '*' in production.")
            if self.db_echo:
                raise ValueError("DB_ECHO must be off in production (it prints query values to the logs).")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
