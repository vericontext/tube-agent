"""Tests for system status helpers and endpoints."""

import json
import os
import threading
import time

import pytest

from tube_agent.api.routes import system as system_route
from tube_agent import config as config_module


def _set_status(value: str) -> None:
    with system_route._lock:
        system_route._state["status"] = value


def test_wait_for_embedding_ready_returns_true_when_already_ready(monkeypatch):
    _set_status("ready")
    try:
        assert system_route.wait_for_embedding_ready(timeout=1.0) is True
    finally:
        _set_status("idle")


def test_wait_for_embedding_ready_returns_false_on_failed():
    _set_status("failed")
    try:
        assert system_route.wait_for_embedding_ready(timeout=1.0) is False
    finally:
        _set_status("idle")


def test_wait_for_embedding_ready_times_out_when_loading():
    _set_status("loading")
    try:
        start = time.monotonic()
        assert system_route.wait_for_embedding_ready(timeout=0.5) is False
        elapsed = time.monotonic() - start
        assert 0.4 <= elapsed <= 1.5  # roughly the timeout window
    finally:
        _set_status("idle")


def test_wait_for_embedding_ready_unblocks_when_state_flips():
    _set_status("loading")

    def _flip_after_delay():
        time.sleep(0.3)
        _set_status("ready")

    flipper = threading.Thread(target=_flip_after_delay, daemon=True)
    flipper.start()
    try:
        assert system_route.wait_for_embedding_ready(timeout=2.0) is True
    finally:
        flipper.join(timeout=1.0)
        _set_status("idle")


# --- Secrets / settings -------------------------------------------------------


@pytest.fixture
def isolated_app_data(tmp_path, monkeypatch):
    """Point Settings at a fresh tmp dir and clear API-key env vars."""
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config_module.get_settings.cache_clear()
    config_module._secrets_cache = None
    yield tmp_path
    config_module.get_settings.cache_clear()
    config_module._secrets_cache = None


def test_secrets_status_unset_on_fresh_install(isolated_app_data):
    s = config_module.Settings()
    assert s.secrets_status() == {"youtube_api_key": "unset", "gemini_api_key": "unset"}
    assert s.youtube_api_key == ""
    assert s.gemini_api_key == ""


def test_secrets_round_trip(isolated_app_data):
    s = config_module.Settings()
    s.update_secrets({"youtube_api_key": "yt-key-1", "gemini_api_key": "gm-key-1"})

    secrets_path = isolated_app_data / "secrets.json"
    assert secrets_path.exists()
    assert json.loads(secrets_path.read_text()) == {
        "youtube_api_key": "yt-key-1",
        "gemini_api_key": "gm-key-1",
    }
    if os.name != "nt":
        # 0o600 only meaningful on POSIX
        assert oct(secrets_path.stat().st_mode & 0o777) == "0o600"

    s2 = config_module.Settings()
    assert s2.youtube_api_key == "yt-key-1"
    assert s2.secrets_status() == {"youtube_api_key": "set", "gemini_api_key": "set"}


def test_secrets_empty_value_clears_key(isolated_app_data):
    s = config_module.Settings()
    s.update_secrets({"youtube_api_key": "yt-key-1"})
    assert s.youtube_api_key == "yt-key-1"

    s.update_secrets({"youtube_api_key": ""})
    assert s.youtube_api_key == ""
    assert s.secrets_status()["youtube_api_key"] == "unset"


def test_env_var_wins_over_secrets(isolated_app_data, monkeypatch):
    s = config_module.Settings()
    s.update_secrets({"youtube_api_key": "from-file"})
    monkeypatch.setenv("YOUTUBE_API_KEY", "from-env")
    assert s.youtube_api_key == "from-env"


def test_concurrent_writes_keep_json_coherent(isolated_app_data):
    s = config_module.Settings()

    def writer(value: str):
        for _ in range(20):
            s.update_secrets({"youtube_api_key": value})

    t1 = threading.Thread(target=writer, args=("aaa",))
    t2 = threading.Thread(target=writer, args=("bbb",))
    t1.start(); t2.start()
    t1.join(); t2.join()

    # Whatever last-write wins, the file is parseable and has one of the values.
    body = (isolated_app_data / "secrets.json").read_text()
    parsed = json.loads(body)  # raises if the file is half-written
    assert parsed["youtube_api_key"] in {"aaa", "bbb"}


def test_settings_endpoint_get_post_round_trip(client, isolated_app_data):
    resp = client.get("/api/v1/system/settings")
    assert resp.status_code == 200
    assert resp.json()["youtube_api_key"] == "unset"

    resp = client.post(
        "/api/v1/system/settings",
        json={"youtube_api_key": "abc-123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["youtube_api_key"] == "set"
    assert body["gemini_api_key"] == "unset"

    # Persisted across a fresh Settings() lookup.
    assert config_module.Settings().youtube_api_key == "abc-123"


def test_settings_test_endpoint_rejects_empty_key(client):
    resp = client.post(
        "/api/v1/system/settings/test",
        json={"provider": "youtube", "api_key": ""},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "empty" in (body["error"] or "").lower()
