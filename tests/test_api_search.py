"""Tests for search API endpoint."""


class TestSearch:
    def test_search_videos(self, seeded_client):
        resp = seeded_client.get("/api/v1/search?q=Test Video")
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "Test Video"
        assert data["total"] > 0
        video_results = [r for r in data["results"] if r["type"] == "video"]
        assert len(video_results) > 0

    def test_search_type_filter(self, seeded_client):
        resp = seeded_client.get("/api/v1/search?q=testing&type=summaries")
        assert resp.status_code == 200
        data = resp.json()
        for r in data["results"]:
            assert r["type"] == "summary"

    def test_search_videos_only(self, seeded_client):
        resp = seeded_client.get("/api/v1/search?q=Test&type=videos")
        assert resp.status_code == 200
        for r in resp.json()["results"]:
            assert r["type"] == "video"

    def test_search_transcripts(self, seeded_client):
        resp = seeded_client.get("/api/v1/search?q=pricing&type=transcripts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        result = data["results"][0]
        assert result["type"] == "transcript"
        assert result["timestamp"] == "00:12"
        assert result["youtube_url"].endswith("&t=12s")
        assert result["channel_handle"] == "testchannel"

    def test_search_no_results(self, seeded_client):
        resp = seeded_client.get("/api/v1/search?q=zzz_nonexistent_zzz")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_search_empty_query(self, client):
        resp = client.get("/api/v1/search?q=")
        assert resp.status_code == 422
