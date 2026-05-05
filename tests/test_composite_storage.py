"""Tests for CompositeStorage fan-out behavior."""

import pytest

from tube_agent.storage.local import LocalStorage
from tube_agent.storage.composite import CompositeStorage
from tube_agent.storage.base import StorageBackend
from tests.conftest import SAMPLE_CHANNEL, SAMPLE_VIDEOS, SAMPLE_ANALYSIS


class FakeStorage(StorageBackend):
    """Minimal in-memory storage for testing."""

    def __init__(self, fail_on: set[str] | None = None):
        self.calls: list[tuple[str, tuple]] = []
        self._fail_on = fail_on or set()

    def _record(self, method, *args, **kwargs):
        self.calls.append((method, args))
        if method in self._fail_on:
            raise RuntimeError(f"Simulated failure in {method}")

    def save_channel(self, data):
        self._record("save_channel", data)
        return data.get("id", "")

    def get_channel(self, handle):
        return None

    def list_channels(self, offset=0, limit=50):
        return [], 0

    def save_videos(self, channel_id, videos):
        self._record("save_videos", channel_id, videos)
        return len(videos)

    def get_video(self, video_id):
        return None

    def list_videos(self, channel_id, sort_by="published_at", sort_order="desc", offset=0, limit=50):
        return [], 0

    def save_comments(self, video_id, comments):
        self._record("save_comments", video_id, comments)
        return len(comments)

    def get_comments(self, video_id, offset=0, limit=100):
        return [], 0

    def has_comments(self, video_id):
        return False

    def save_summary(self, video_id, title, analysis):
        self._record("save_summary", video_id, title, analysis)

    def get_summary(self, video_id):
        return None

    def has_summary(self, video_id):
        return False

    def save_transcript_segments(self, video_id, language, source, segments):
        self._record("save_transcript_segments", video_id, language, source, segments)
        return len(segments)

    def get_transcript(self, video_id, language=None):
        return []

    def has_transcript(self, video_id, language=None):
        return False

    def search_transcripts(self, q, limit=20, channel_id=None):
        return []

    def save_report(self, channel_id, report_type, content_md, tenant_id=None):
        self._record("save_report", channel_id, report_type, content_md)
        return "fake-id"

    def get_report(self, channel_id, report_type, tenant_id=None):
        return None

    def list_reports(self, channel_id, tenant_id=None):
        return []

    def create_job(self, job_data):
        return "job-1"

    def get_job(self, job_id):
        return None

    def update_job(self, job_id, updates):
        pass


class TestCompositeWrites:
    def test_save_channel_propagates(self, tmp_path):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        composite.save_channel(SAMPLE_CHANNEL)

        assert any(m == "save_channel" for m, _ in primary.calls)
        assert any(m == "save_channel" for m, _ in secondary.calls)

    def test_save_videos_propagates(self, tmp_path):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        composite.save_videos("ch1", SAMPLE_VIDEOS)

        assert any(m == "save_videos" for m, _ in primary.calls)
        assert any(m == "save_videos" for m, _ in secondary.calls)

    def test_save_comments_propagates(self):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        composite.save_comments("vid_1", [{"author": "A", "text": "Hi"}])

        assert any(m == "save_comments" for m, _ in primary.calls)
        assert any(m == "save_comments" for m, _ in secondary.calls)

    def test_save_summary_propagates(self):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        composite.save_summary("vid_1", "Title", SAMPLE_ANALYSIS)

        assert any(m == "save_summary" for m, _ in primary.calls)
        assert any(m == "save_summary" for m, _ in secondary.calls)

    def test_save_report_propagates(self):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        composite.save_report("ch1", "overview", "# Report")

        assert any(m == "save_report" for m, _ in primary.calls)
        assert any(m == "save_report" for m, _ in secondary.calls)

    def test_save_transcript_segments_propagates(self):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        composite.save_transcript_segments("vid_1", "en", "manual", [{"text": "hello"}])

        assert any(m == "save_transcript_segments" for m, _ in primary.calls)
        assert any(m == "save_transcript_segments" for m, _ in secondary.calls)


class TestCompositeReads:
    def test_reads_from_primary_only(self):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        composite.get_channel("test")
        composite.get_video("vid_1")
        composite.get_summary("vid_1")
        composite.has_comments("vid_1")
        composite.has_summary("vid_1")
        composite.has_transcript("vid_1")
        composite.get_transcript("vid_1")
        composite.search_transcripts("hello")
        composite.get_report("ch1", "overview")
        composite.list_reports("ch1")

        # Secondary should have no calls (reads don't touch it)
        assert len(secondary.calls) == 0


class TestCompositeSecondaryFailure:
    def test_secondary_failure_does_not_abort(self):
        primary = FakeStorage()
        failing = FakeStorage(fail_on={"save_channel", "save_videos", "save_summary"})
        composite = CompositeStorage(primary, failing)

        # These should succeed despite secondary failures
        result = composite.save_channel(SAMPLE_CHANNEL)
        assert result == SAMPLE_CHANNEL["id"]

        count = composite.save_videos("ch1", SAMPLE_VIDEOS)
        assert count == len(SAMPLE_VIDEOS)

        composite.save_summary("vid_1", "Title", SAMPLE_ANALYSIS)
        # No exception raised

    def test_primary_result_returned(self):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        result = composite.save_channel(SAMPLE_CHANNEL)
        assert result == SAMPLE_CHANNEL["id"]


class TestCompositeJobs:
    def test_jobs_primary_only(self):
        primary = FakeStorage()
        secondary = FakeStorage()
        composite = CompositeStorage(primary, secondary)

        job_id = composite.create_job({"type": "test"})
        assert job_id == "job-1"

        composite.get_job(job_id)
        composite.update_job(job_id, {"status": "done"})

        # Secondary should not be touched for job ops
        assert len(secondary.calls) == 0
