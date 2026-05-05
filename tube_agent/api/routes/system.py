"""System / readiness endpoints.

The embedding model is large (~220 MB on first run) and downloading it on
first request would block the UI for tens of seconds. Instead the sidecar
warms the provider in a background thread at startup; this router exposes
the warmup state so the desktop app can render an unobtrusive pill.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from tube_agent.config import get_settings
from tube_agent.models.schemas import (
    SettingsStatus,
    SettingsTest,
    SettingsTestResult,
    SettingsUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

_state: dict[str, Any] = {"status": "idle", "model": None, "error": None}
_lock = threading.Lock()
_thread: threading.Thread | None = None


def wait_for_embedding_ready(timeout: float = 90.0) -> bool:
    """Block (polling) until the embedding warmup finishes or fails.

    Returns ``True`` once the model is loaded, ``False`` if the warmup
    failed or did not complete within ``timeout`` seconds.
    """
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        with _lock:
            status = _state["status"]
        if status == "ready":
            return True
        if status == "failed":
            return False
        time.sleep(0.25)
    return False


def _warmup() -> None:
    try:
        with _lock:
            _state["status"] = "loading"
        from tube_agent.services.embeddings import get_default_provider

        provider = get_default_provider()
        with _lock:
            _state["status"] = "ready"
            _state["model"] = provider.name
            _state["error"] = None
        logger.info("Embedding provider ready: %s", provider.name)
    except Exception as e:
        logger.error("Embedding warmup failed: %s", e)
        with _lock:
            _state["status"] = "failed"
            _state["error"] = str(e)


def start_warmup() -> None:
    """Kick off background embedding-model load if it hasn't run yet."""
    global _thread
    with _lock:
        if _state["status"] in ("loading", "ready"):
            return
        if _thread is not None and _thread.is_alive():
            return
        _state["status"] = "idle"
        _state["error"] = None
    _thread = threading.Thread(target=_warmup, daemon=True, name="embedding-warmup")
    _thread.start()


@router.get("/embedding-status")
def embedding_status() -> dict[str, Any]:
    """Return current embedding-model warmup state."""
    with _lock:
        return dict(_state)


@router.post("/embedding/prepare", status_code=202)
def prepare_embedding() -> dict[str, Any]:
    """Trigger (or re-trigger after failure) the embedding-model warmup."""
    start_warmup()
    with _lock:
        return dict(_state)


# --- Settings -----------------------------------------------------------------


def _settings_status() -> SettingsStatus:
    settings = get_settings()
    status = settings.secrets_status()
    return SettingsStatus(
        youtube_api_key=status["youtube_api_key"],
        gemini_api_key=status["gemini_api_key"],
        app_data_dir=str(settings.resolve_app_data_dir()),
    )


@router.get("/settings", response_model=SettingsStatus)
def get_settings_status() -> SettingsStatus:
    """Return whether each API key is currently configured. Never leaks values."""
    return _settings_status()


@router.post("/settings", response_model=SettingsStatus)
def update_settings(body: SettingsUpdate) -> SettingsStatus:
    """Persist API keys to ``secrets.json``. Empty string clears a key."""
    updates: dict[str, str | None] = {}
    if body.youtube_api_key is not None:
        updates["youtube_api_key"] = body.youtube_api_key
    if body.gemini_api_key is not None:
        updates["gemini_api_key"] = body.gemini_api_key
    if updates:
        get_settings().update_secrets(updates)
    return _settings_status()


@router.post("/settings/test", response_model=SettingsTestResult)
def test_settings_key(body: SettingsTest) -> SettingsTestResult:
    """Validate an API key by making a single live request to the provider."""
    if not body.api_key:
        return SettingsTestResult(ok=False, error="API key is empty")
    try:
        with httpx.Client(timeout=5.0) as client:
            if body.provider == "youtube":
                r = client.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"forHandle": "ycombinator", "part": "id", "key": body.api_key},
                )
            elif body.provider == "gemini":
                r = client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": body.api_key},
                )
            else:
                raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")

            if r.status_code == 200:
                return SettingsTestResult(ok=True)
            try:
                detail = r.json().get("error", {}).get("message", r.text)
            except Exception:
                detail = r.text
            return SettingsTestResult(ok=False, error=f"HTTP {r.status_code}: {detail}")
    except httpx.TimeoutException:
        return SettingsTestResult(ok=False, error="Request timed out after 5s")
    except httpx.HTTPError as e:
        return SettingsTestResult(ok=False, error=f"Network error: {e}")
