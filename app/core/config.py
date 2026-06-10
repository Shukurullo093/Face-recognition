"""Application configuration via Pydantic Settings (12-factor, env-driven)."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, validated settings. Loaded once and cached."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "Face Recognition System"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # ---- Database ----
    POSTGRES_USER: str = "face"
    POSTGRES_PASSWORD: str = "face_password"
    POSTGRES_DB: str = "facedb"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # ---- Security ----
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    RATE_LIMIT: str = "100/minute"

    # ---- Recognition models ----
    # Relative paths resolve from the working dir (project root locally, /app in
    # Docker where ./models is mounted to /app/models) — consistent in both.
    DETECTOR_MODEL_PATH: str = "./models/scrfd_2.5g_bnkps.onnx"
    ARCFACE_MODEL_PATH: str = "./models/arcface_r100.onnx"
    ONNX_PROVIDERS: str = "CUDAExecutionProvider,CPUExecutionProvider"
    DETECTION_INPUT_SIZE: int = 640
    DETECTION_THRESHOLD: float = 0.5
    DETECTION_NMS_THRESHOLD: float = 0.4
    RECOGNITION_THRESHOLD: float = 0.35
    MIN_FACE_SIZE: int = 40

    # ---- Search ----
    SEARCH_TOP_K: int = 10
    HNSW_EF_SEARCH: int = 80

    # ---- Bulk import ----
    IMPORT_BATCH_SIZE: int = 32
    IMPORT_MAX_WORKERS: int = 4

    @computed_field  # type: ignore[prop-decorator]
    @property
    def onnx_providers_list(self) -> list[str]:
        return [p.strip() for p in self.ONNX_PROVIDERS.split(",") if p.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy DSN (asyncpg driver)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Sync DSN used by Alembic migrations."""
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import this everywhere."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
