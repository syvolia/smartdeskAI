"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]

_DEV_SECRET = "dev-insecure-secret-change-me"


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

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "smartdesk"
    postgres_password: str = "smartdesk"
    postgres_db: str = "smartdesk"

    # --- Redis ---
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
    ai_provider: str = "auto"  # "auto" | "openai" | "mock"

    # --- Embeddings / RAG ---
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_provider: str = "auto"  # "auto" | "openai" | "mock"
    knowledge_chunk_target_tokens: int = 400
    knowledge_chunk_overlap_tokens: int = 60
    knowledge_search_default_top_k: int = 5
    knowledge_search_min_similarity: float = 0.2
    knowledge_rag_min_similarity: float = 0.25

    # --- Derived URLs ---

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
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
    return Settings()


settings = get_settings()