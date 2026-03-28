"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./tube_agent.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API Keys
    youtube_api_key: str = ""
    gemini_api_key: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # R2 / S3 (optional)
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "tube-agent"

    # App
    api_prefix: str = "/api/v1"
    debug: bool = False
    cors_origins: str = "*"  # Comma-separated list of allowed origins

    # Auth (Supabase)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""  # If empty, derived from service_role_key

    # Gemini defaults
    default_media_resolution: str = "low"
    default_max_videos: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
