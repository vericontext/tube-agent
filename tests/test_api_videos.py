"""Tests for video and summary API endpoints."""


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
