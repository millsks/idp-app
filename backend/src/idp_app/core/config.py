"""Application configuration via pydantic-settings.

Settings are loaded from environment variables (or a .env file).
"""

from functools import lru_cache
from typing import Annotated

from pydantic import PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "Integrated Developer Portal"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # API
    API_V1_PREFIX: str = "/api/v1"
    # Comma-separated origins, e.g. "http://localhost:3000,https://app.example.com".
    # Stored as a plain string so pydantic-settings passes the env var verbatim
    # (complex types like list[str] trigger a JSON-decode attempt that fails for
    # plain URL strings).  parse_allowed_origins() returns the split list.
    ALLOWED_ORIGINS: str = ""

    def parse_allowed_origins(self) -> list[str]:
        """Return ALLOWED_ORIGINS split on commas, with blanks filtered out."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # ------------------------------------------------------------------
    # Database (PostgreSQL)
    # Compose the URL from discrete fields so credentials are never
    # embedded as a default literal.  Set DB_USER / DB_PASSWORD in .env
    # or as environment variables.  DATABASE_URL can be set directly to
    # override the assembled value (e.g. in CI or production).
    # ------------------------------------------------------------------
    DB_USER: str = "idp_user"
    DB_PASSWORD: str | None = None  # required when DATABASE_URL is not set directly
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "idp_db"
    DATABASE_URL: PostgresDsn | None = None

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        """Build DATABASE_URL from components when not provided directly."""
        if self.DATABASE_URL is None:
            if not self.DB_PASSWORD:
                raise ValueError(
                    "DB_PASSWORD must be set when DATABASE_URL is not provided directly."
                )
            self.DATABASE_URL = PostgresDsn(
                f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return self

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")

    # ------------------------------------------------------------------
    # Celery
    # ------------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_ALWAYS_EAGER: bool = False  # Set True in tests to run tasks synchronously


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()


# Convenience alias used throughout the application
SettingsDep = Annotated[Settings, None]
