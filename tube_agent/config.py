"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./tube_agent.db"

    # API Keys
    youtube_api_key: str = ""
    gemini_api_key: str = ""

    # App
    api_prefix: str = "/api/v1"
    debug: bool = False
    cors_origins: str = "*"  # Comma-separated list of allowed origins

    # Gemini defaults
    default_media_resolution: str = "low"
    default_max_videos: int = 100

    # Embeddings
    embedding_provider: str = "local"  # local | gemini
    embedding_model: str = ""  # empty = provider default

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
