"""Tests for channel API endpoints."""

import pytest

from tests.conftest import SAMPLE_CHANNEL


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Replace the pipeline runner so POST /channels doesn't hit YouTube/Gemini/embedder."""
    from tube_agent.api.routes import channels as channels_route

    def _fake(*, handle, **kwargs):
        return {"channel_id": f"UC_{handle}", "handle": handle, "video_count": 0}

    def _fake_provider():
        raise RuntimeError("disabled in tests")

    monkeypatch.setattr(channels_route, "run_full_pipeline", _fake)
    monkeypatch.setattr(channels_route, "get_default_provider", _fake_provider)


class TestListChannels:
    def test_empty_db(self, client):
        resp = client.get("/api/v1/channels")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["channels"] == []

    def test_with_data(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["channels"][0]["handle"] == "testchannel"


class TestGetChannel:
    def test_found(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == SAMPLE_CHANNEL["id"]
        assert data["title"] == "Test Channel"

    def test_with_at_prefix(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/@testchannel")
        assert resp.status_code == 200

    def test_not_found(self, client):
        resp = client.get("/api/v1/channels/nonexistent")
        assert resp.status_code == 404


class TestCreateChannel:
    def test_creates_job(self, client, stub_pipeline):
        resp = client.post("/api/v1/channels", json={"handle": "test"})
        assert resp.status_code == 202
        data = resp.json()
        assert "id" in data
        assert data["job_type"] == "full_pipeline"
