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
    # "json": one JSON object per line, for a log collector (production). "text": easy to read.
    log_format: Literal["text", "json"] = "text"
    # Prometheus metrics are served on this port by the API and by the worker (each its own port in
    # Docker); never on the API's own port. 0 = off.
    metrics_port: int = Field(default=0, ge=0, le=65535)
    api_v1_prefix: str = "/api/v1"
    # Comma-separated list of frontend addresses allowed to call this API.
    cors_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://eduguide:eduguide@localhost:5432/eduguide"
    db_echo: bool = False

    # ---- Redis (Step 12) ----
    # Empty: background jobs run inside the API process and rate limits are counted in its memory
    # (fine for one computer). Set (e.g. redis://localhost:6379/0): jobs go to Redis and are run by
    # `python -m app.worker`; the limits are shared by every API process. Required in production.
    redis_url: str = ""

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

    # ---- AI model (docs/06-llm-interfaces.md) ----
    # "none": AI features answer 503 `ai_not_configured`. "anthropic": Claude. "groq": open models on
    # Groq, which has a free plan (with low limits per minute and per day).
    llm_provider: Literal["none", "anthropic", "groq"] = "none"
    anthropic_api_key: str = ""  # required when LLM_PROVIDER=anthropic
    groq_api_key: str = ""  # required when LLM_PROVIDER=groq
    # One model per tier; empty = the provider's own choice (DEFAULT_MODELS in its adapter). The tiers
    # also differ in effort (fast = low, default = medium, strong = high).
    llm_model_fast: str = ""
    llm_model_default: str = ""
    llm_model_strong: str = ""

    # ---- Search inside books ----
    # Folder for the local search model (~1 GB, downloaded on first use). Relative to backend/.
    model_cache_dir: str = "storage/models"

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
    def _ai_key_must_be_set(self) -> "Settings":
        keys = {"anthropic": self.anthropic_api_key, "groq": self.groq_api_key}
        if self.llm_provider in keys and not keys[self.llm_provider]:
            name = f"{self.llm_provider.upper()}_API_KEY"
            raise ValueError(f"LLM_PROVIDER={self.llm_provider} needs {name} in backend/.env.")
        return self

    @model_validator(mode="after")
    def _production_must_be_locked_down(self) -> "Settings":
        if self.environment == "production":
            if "*" in self.cors_origin_list:
                raise ValueError("CORS_ORIGINS cannot contain '*' in production.")
            if self.db_echo:
                raise ValueError("DB_ECHO must be off in production (it prints query values to the logs).")
            if not self.redis_url:
                raise ValueError("REDIS_URL is required in production (background workers, rate limits).")
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
        return _backend_path(self.storage_dir)

    @property
    def model_cache_path(self) -> Path:
        return _backend_path(self.model_cache_dir)


def _backend_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
