"""Application configuration using pydantic-settings.

Resolves the per-OS app data directory at runtime so the same code runs both
in repo-local dev and inside a Tauri desktop bundle. Override either path
via the ``APP_DATA_DIR`` or ``DATABASE_URL`` env var.
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


def _default_app_data_dir() -> Path:
    """Return the OS-conventional per-user data directory for tube-agent."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "tube-agent"
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "tube-agent"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "tube-agent"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Per-OS app data dir; empty value resolves to the platform default
    # (e.g. ~/Library/Application Support/tube-agent on macOS).
    app_data_dir: str = ""

    # Database — empty value is derived from app_data_dir at runtime
    database_url: str = ""

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

    def resolve_app_data_dir(self) -> Path:
        """Return the resolved app data dir, creating it if missing."""
        path = Path(self.app_data_dir) if self.app_data_dir else _default_app_data_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_database_url(self) -> str:
        """Return the SQLAlchemy URL, defaulting to a SQLite DB inside app_data_dir."""
        if self.database_url:
            return self.database_url
        db_path = self.resolve_app_data_dir() / "tube_agent.db"
        return f"sqlite:///{db_path}"

    def resolve_fastembed_cache_dir(self) -> Path:
        """Cache directory for fastembed downloads (kept inside app_data_dir)."""
        cache = self.resolve_app_data_dir() / "fastembed_cache"
        cache.mkdir(parents=True, exist_ok=True)
        return cache


@lru_cache
def get_settings() -> Settings:
    return Settings()
