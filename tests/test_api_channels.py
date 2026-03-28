"""Tests for channel API endpoints."""

from tests.conftest import SAMPLE_CHANNEL


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
    def test_no_auth(self, client):
        resp = client.post("/api/v1/channels", json={"handle": "test"})
        assert resp.status_code == 401

    def test_invalid_token(self, client):
        resp = client.post(
            "/api/v1/channels",
            json={"handle": "test"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401
