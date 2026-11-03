"""Application settings.

Every value comes from an environment variable or from the `.env` file in the
`backend/` folder. Nothing secret is hard-coded.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
