"""Tests for PostgresStorage CRUD operations."""

from tests.conftest import SAMPLE_CHANNEL, SAMPLE_VIDEOS, SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT


class TestChannelStorage:
    def test_save_and_get(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        ch = storage.get_channel("testchannel")
        assert ch is not None
        assert ch["id"] == SAMPLE_CHANNEL["id"]
        assert ch["title"] == "Test Channel"

    def test_get_nonexistent(self, storage):
        assert storage.get_channel("nonexistent") is None

    def test_list_channels(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        channels, total = storage.list_channels()
        assert total == 1
        assert channels[0]["handle"] == "testchannel"

    def test_update_channel(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        updated = {**SAMPLE_CHANNEL, "title": "Updated Title"}
        storage.save_channel(updated)
        ch = storage.get_channel("testchannel")
        assert ch["title"] == "Updated Title"


class TestVideoStorage:
    def test_save_and_list(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        count = storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS)
        assert count == 5

        videos, total = storage.list_videos(SAMPLE_CHANNEL["id"])
        assert total == 5
        assert len(videos) == 5

    def test_sort_by_view_count(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS)

        videos, _ = storage.list_videos(SAMPLE_CHANNEL["id"], sort_by="view_count", sort_order="desc")
        views = [v["view_count"] for v in videos]
        assert views == sorted(views, reverse=True)

    def test_empty_videos(self, storage):
        assert storage.save_videos("ch1", []) == 0


class TestCommentStorage:
    def test_save_and_has(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS[:1])

        assert storage.has_comments("vid_1") is False

        storage.save_comments("vid_1", [
            {"author": "User1", "text": "Great video!", "likeCount": 5},
            {"author": "User2", "text": "Thanks!", "likeCount": 2},
        ])
        assert storage.has_comments("vid_1") is True

    def test_get_comments(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS[:1])
        storage.save_comments("vid_1", [
            {"author": "User1", "text": "Great!", "likeCount": 10},
            {"author": "User2", "text": "Nice!", "likeCount": 3},
        ])

        comments, total = storage.get_comments("vid_1")
        assert total == 2
        assert comments[0]["like_count"] >= comments[1]["like_count"]


class TestSummaryStorage:
    def test_save_and_get(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS[:1])

        assert storage.has_summary("vid_1") is False

        storage.save_summary("vid_1", "Test Video 1", SAMPLE_ANALYSIS)

        assert storage.has_summary("vid_1") is True
        summary = storage.get_summary("vid_1")
        assert summary["content_type"] == "tutorial"
        assert "testing" in summary["topics"]
        assert len(summary["sections"]) == 1
        assert len(summary["bullets"]) == 1

    def test_get_nonexistent(self, storage):
        assert storage.get_summary("nonexistent") is None


class TestTranscriptStorage:
    def test_save_and_get(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS[:1])

        assert storage.has_transcript("vid_1") is False

        count = storage.save_transcript_segments("vid_1", "en", "manual", SAMPLE_TRANSCRIPT)

        assert count == 2
        assert storage.has_transcript("vid_1") is True
        transcript = storage.get_transcript("vid_1")
        assert len(transcript) == 2
        assert transcript[0]["timestamp"] == "00:12"
        assert "pricing strategy" in transcript[0]["text"]

    def test_replace_same_language(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS[:1])

        storage.save_transcript_segments("vid_1", "en", "manual", SAMPLE_TRANSCRIPT)
        storage.save_transcript_segments("vid_1", "en", "manual", SAMPLE_TRANSCRIPT[:1])

        transcript = storage.get_transcript("vid_1", "en")
        assert len(transcript) == 1

    def test_search_transcripts(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS[:1])
        storage.save_transcript_segments("vid_1", "en", "manual", SAMPLE_TRANSCRIPT)

        results = storage.search_transcripts("pricing", limit=10)

        assert len(results) == 1
        assert results[0]["video_id"] == "vid_1"
        assert results[0]["channel_handle"] == "testchannel"


class TestReportStorage:
    def test_save_and_get(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        rid = storage.save_report(SAMPLE_CHANNEL["id"], "content_analysis", "# Report\nContent here")
        assert rid is not None

        report = storage.get_report(SAMPLE_CHANNEL["id"], "content_analysis")
        assert report is not None
        assert report["content_md"] == "# Report\nContent here"

    def test_list_reports(self, storage):
        storage.save_channel(SAMPLE_CHANNEL)
        storage.save_report(SAMPLE_CHANNEL["id"], "content_analysis", "Report 1")
        storage.save_report(SAMPLE_CHANNEL["id"], "trend_analysis", "Report 2")

        reports = storage.list_reports(SAMPLE_CHANNEL["id"])
        assert len(reports) == 2

    def test_get_nonexistent(self, storage):
        assert storage.get_report("ch1", "content_analysis") is None


class TestJobStorage:
    def test_create_and_get(self, storage):
        job_id = storage.create_job({"job_type": "full_pipeline", "config": {"handle": "test"}})
        assert job_id is not None

        job = storage.get_job(job_id)
        assert job["status"] == "pending"
        assert job["config"]["handle"] == "test"

    def test_update_job(self, storage):
        job_id = storage.create_job({"job_type": "full_pipeline"})
        storage.update_job(job_id, {"status": "running"})

        job = storage.get_job(job_id)
        assert job["status"] == "running"

        storage.update_job(job_id, {"status": "completed"})
        job = storage.get_job(job_id)
        assert job["status"] == "completed"

    def test_get_nonexistent(self, storage):
        assert storage.get_job("nonexistent-id") is None
