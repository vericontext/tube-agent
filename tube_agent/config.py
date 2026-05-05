"""Application configuration using pydantic-settings.

Resolves the per-OS app data directory at runtime so the same code runs both
in repo-local dev and inside a Tauri desktop bundle. Override either path
via the ``APP_DATA_DIR`` or ``DATABASE_URL`` env var.

API keys live in two places:

- ``os.environ`` — for dev (`.env` loaded relative to cwd) and CI overrides.
- ``{app_data_dir}/secrets.json`` (chmod ``0600``) — for the Tauri desktop
  app, where Finder-launched processes have ``cwd=/`` and never see ``.env``.

The env var wins. ``Settings.youtube_api_key`` / ``.gemini_api_key`` are
properties that resolve in that order on every access, so any call site that
reads them lazily will pick up new values written through the Settings UI
without restarting the sidecar.
"""

import json
import logging
import os
import sys
import tempfile
import threading
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Make .env values available via os.environ. Pydantic also reads .env for
# declared fields, but the API-key properties below short-circuit on
# os.environ first so the dev workflow keeps working.
load_dotenv(override=False)


def _default_app_data_dir() -> Path:
    """Return the OS-conventional per-user data directory for tube-agent."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "tube-agent"
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "tube-agent"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "tube-agent"


_secrets_lock = threading.Lock()
_secrets_cache: tuple[float, dict[str, str]] | None = None


def _secrets_path(app_data_dir: Path) -> Path:
    return app_data_dir / "secrets.json"


def _load_secrets(app_data_dir: Path) -> dict[str, str]:
    """Read ``secrets.json`` (mtime-cached). Empty dict on missing/corrupt."""
    global _secrets_cache
    path = _secrets_path(app_data_dir)
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return {}
    if _secrets_cache is not None and _secrets_cache[0] == mtime:
        return _secrets_cache[1]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("secrets.json must be a JSON object")
    except (OSError, json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to read %s, ignoring: %s", path, e)
        return {}
    cleaned = {str(k): str(v) for k, v in data.items()}
    _secrets_cache = (mtime, cleaned)
    return cleaned


def _save_secrets(app_data_dir: Path, updates: dict[str, str | None]) -> dict[str, str]:
    """Merge ``updates`` into ``secrets.json`` and rewrite atomically.

    A ``None`` value or empty string deletes the corresponding key. Returns
    the new full dict.
    """
    global _secrets_cache
    app_data_dir.mkdir(parents=True, exist_ok=True)
    path = _secrets_path(app_data_dir)
    with _secrets_lock:
        current = _load_secrets(app_data_dir).copy()
        for key, value in updates.items():
            if value:
                current[key] = value
            else:
                current.pop(key, None)
        body = json.dumps(current, ensure_ascii=False, indent=2)

        # Atomic write: tempfile in the same dir → chmod → os.replace.
        fd, tmp_path = tempfile.mkstemp(prefix=".secrets-", dir=str(app_data_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(body)
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        _secrets_cache = (path.stat().st_mtime, current.copy())
        return current


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    ``youtube_api_key`` and ``gemini_api_key`` are deliberately *not* declared
    as pydantic fields — they're properties that fall through env →
    ``secrets.json`` so the desktop UI can write to them without restarting
    the sidecar.
    """

    # Per-OS app data dir; empty value resolves to the platform default
    # (e.g. ~/Library/Application Support/tube-agent on macOS).
    app_data_dir: str = ""

    # Database — empty value is derived from app_data_dir at runtime
    database_url: str = ""

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

    # --- API key resolution -------------------------------------------------

    @property
    def youtube_api_key(self) -> str:
        return os.environ.get("YOUTUBE_API_KEY") or _load_secrets(
            self.resolve_app_data_dir()
        ).get("youtube_api_key", "")

    @property
    def gemini_api_key(self) -> str:
        return os.environ.get("GEMINI_API_KEY") or _load_secrets(
            self.resolve_app_data_dir()
        ).get("gemini_api_key", "")

    def update_secrets(self, updates: dict[str, str | None]) -> dict[str, str]:
        """Persist API keys to ``secrets.json``. Empty/None values delete a key."""
        allowed = {"youtube_api_key", "gemini_api_key"}
        filtered = {k: v for k, v in updates.items() if k in allowed}
        return _save_secrets(self.resolve_app_data_dir(), filtered)

    def secrets_status(self) -> dict[str, Literal["set", "unset"]]:
        """Map of which keys currently resolve to a non-empty value."""
        return {
            "youtube_api_key": "set" if self.youtube_api_key else "unset",
            "gemini_api_key": "set" if self.gemini_api_key else "unset",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
