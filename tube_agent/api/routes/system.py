"""System / readiness endpoints.

The embedding model is large (~220 MB on first run) and downloading it on
first request would block the UI for tens of seconds. Instead the sidecar
warms the provider in a background thread at startup; this router exposes
the warmup state so the desktop app can render an unobtrusive pill.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

_state: dict[str, Any] = {"status": "idle", "model": None, "error": None}
_lock = threading.Lock()
_thread: threading.Thread | None = None


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
