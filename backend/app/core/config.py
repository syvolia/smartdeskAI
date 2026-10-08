"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]

_DEV_SECRET = "dev-insecure-secret-change-me"


def _normalize_async_db_url(url: str) -> str:
    """SQLAlchemy async needs `postgresql+asyncpg://`, and asyncpg wants
    `ssl=` not `sslmode=`. This normalizes whatever the platform gave us."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    # asyncpg rejects `sslmode`; it accepts `ssl`.
    url = url.replace("sslmode=require", "ssl=require")
    url = url.replace("sslmode=prefer", "ssl=prefer")
    url = url.replace("sslmode=disable", "ssl=disable")
    return url


def _normalize_sync_db_url(url: str) -> str:
    """Same normalization for the sync driver used by Alembic."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "SmartDesk AI"
    app_env: Environment = "development"
    app_debug: bool = True
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = False

    # --- CORS ---
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                import json

                return json.loads(value)
            return [o.strip() for o in value.split(",") if o.strip()]
        return value

    # --- Explicit DATABASE_URL / REDIS_URL (managed-host overrides) ---
    # These are declared as fields so pydantic-settings picks them up from
    # the environment without any custom property logic.
    database_url_raw: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url_raw: str | None = Field(default=None, alias="REDIS_URL")

    # --- PostgreSQL components (fallback when DATABASE_URL isn't set) ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "smartdesk"
    postgres_password: str = "smartdesk"
    postgres_db: str = "smartdesk"

    # --- Redis components (fallback when REDIS_URL isn't set) ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # --- Auth ---
    jwt_secret_key: str = _DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- AI ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0
    ai_provider: str = "auto"

    # --- Embeddings / RAG ---
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_provider: str = "auto"
    knowledge_chunk_target_tokens: int = 400
    knowledge_chunk_overlap_tokens: int = 60
    knowledge_search_default_top_k: int = 5
    knowledge_search_min_similarity: float = 0.2
    knowledge_rag_min_similarity: float = 0.25

    # --- Derived URLs ---

    @property
    def database_url(self) -> str:
        """Async URL for SQLAlchemy."""
        if self.database_url_raw:
            return _normalize_async_db_url(self.database_url_raw)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic."""
        if self.database_url_raw:
            return _normalize_sync_db_url(self.database_url_raw)
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_url_raw:
            return self.redis_url_raw.strip()
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _guard_production_secret(self) -> "Settings":
        if self.is_production and self.jwt_secret_key == _DEV_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a real secret when APP_ENV=production."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()

    # One-time startup log so we can see exactly what the app resolved.
    import os

    import structlog

    log = structlog.get_logger("config")

    def _redact(url: str) -> str:
        # Strip anything that looks like a password between : and @.
        import re

        return re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", url)

    log.info(
        "settings_loaded",
        app_env=settings.app_env,
        database_url=_redact(settings.database_url),
        redis_url=_redact(settings.redis_url),
        database_url_from_env="DATABASE_URL" in os.environ,
        redis_url_from_env="REDIS_URL" in os.environ,
    )

    return settings


settings = get_settings()