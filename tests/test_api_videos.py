"""Tests for video and summary API endpoints."""

from tests.conftest import SAMPLE_TRANSCRIPT
from tests.test_summaries import _summary_json
from tube_agent.services.transcripts import TranscriptResult, TranscriptUnavailableError


class _Settings:
    gemini_api_key = "gemini-test-key"


class _NoKeySettings:
    gemini_api_key = ""


class _FakeGemini:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate_text(self, prompt):
        return _summary_json()


class _FakeTranscriptExtractor:
    def __init__(self, languages):
        self.languages = languages

    def extract(self, video_id):
        return TranscriptResult(
            video_id=video_id,
            language="en",
            source="manual",
            segments=SAMPLE_TRANSCRIPT,
        )


class TestListVideos:
    def test_list_videos(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["videos"]) == 5

    def test_sort_by_view_count(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel/videos?sort_by=view_count&sort_order=desc")
        assert resp.status_code == 200
        views = [v["view_count"] for v in resp.json()["videos"]]
        assert views == sorted(views, reverse=True)

    def test_pagination(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel/videos?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["videos"]) == 2
        assert data["total"] == 5

    def test_channel_not_found(self, client):
        resp = client.get("/api/v1/channels/nonexistent/videos")
        assert resp.status_code == 404


class TestGetVideoSummary:
    def test_found(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel/videos/vid_1/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "vid_1"
        assert "testing" in data["topics"]
        assert data["content_type"] == "tutorial"

    def test_not_found(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel/videos/vid_999/summary")
        assert resp.status_code == 404


class TestGenerateVideoSummary:
    def test_generate_from_transcript(self, seeded_client, monkeypatch):
        from tube_agent.api.routes import videos as videos_route

        monkeypatch.setattr(videos_route, "get_settings", lambda: _Settings())
        monkeypatch.setattr(videos_route, "GeminiClient", _FakeGemini)

        resp = seeded_client.post("/api/v1/channels/testchannel/videos/vid_1/summary", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "vid_1"
        assert "pricing" in data["topics"]
        assert data["bullets"][0]["timestamp"] == "00:12"

    def test_generate_requires_gemini_key(self, seeded_client, monkeypatch):
        from tube_agent.api.routes import videos as videos_route

        monkeypatch.setattr(videos_route, "get_settings", lambda: _NoKeySettings())

        resp = seeded_client.post("/api/v1/channels/testchannel/videos/vid_1/summary", json={})

        assert resp.status_code == 400
        assert "Gemini API key" in resp.json()["detail"]

    def test_generate_requires_transcript(self, seeded_client, monkeypatch):
        from tube_agent.api.routes import videos as videos_route

        monkeypatch.setattr(videos_route, "get_settings", lambda: _Settings())
        monkeypatch.setattr(videos_route, "GeminiClient", _FakeGemini)

        resp = seeded_client.post("/api/v1/channels/testchannel/videos/vid_2/summary", json={})

        assert resp.status_code == 400
        assert "Transcript not found" in resp.json()["detail"]


class TestGetVideoTranscript:
    def test_found(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel/videos/vid_1/transcript")
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "vid_1"
        assert data["language"] == "en"
        assert len(data["segments"]) == 2
        assert data["segments"][0]["timestamp"] == "00:12"

    def test_empty(self, seeded_client):
        resp = seeded_client.get("/api/v1/channels/testchannel/videos/vid_2/transcript")
        assert resp.status_code == 200
        assert resp.json()["segments"] == []


class TestFetchVideoTranscript:
    def test_fetch_and_store_transcript(self, seeded_client, monkeypatch):
        from tube_agent.api.routes import videos as videos_route

        monkeypatch.setattr(videos_route, "TranscriptExtractor", _FakeTranscriptExtractor)

        resp = seeded_client.post(
            "/api/v1/channels/testchannel/videos/vid_2/transcript",
            json={"languages": ["ko", "en"], "embed": False},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "vid_2"
        assert data["language"] == "en"
        assert len(data["segments"]) == 2

        stored = seeded_client.get("/api/v1/channels/testchannel/videos/vid_2/transcript")
        assert len(stored.json()["segments"]) == 2

    def test_fetch_transcript_surfaces_rate_limit(self, seeded_client, monkeypatch):
        from tube_agent.api.routes import videos as videos_route

        class RateLimitedExtractor:
            def __init__(self, languages):
                self.languages = languages

            def extract(self, video_id):
                raise TranscriptUnavailableError("YouTube transcript endpoint rate-limited (HTTP 429)")

        monkeypatch.setattr(videos_route, "TranscriptExtractor", RateLimitedExtractor)

        resp = seeded_client.post(
            "/api/v1/channels/testchannel/videos/vid_2/transcript",
            json={"embed": False},
        )

        assert resp.status_code == 429
        assert "HTTP 429" in resp.json()["detail"]
