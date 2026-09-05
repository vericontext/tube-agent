"""Tests for the app-level indexing pipeline orchestration.

These tests keep external services fake so they exercise the same control flow
the Tauri app uses without touching YouTube, Gemini, or the local ONNX model.
"""

import numpy as np

from tests.conftest import SAMPLE_TRANSCRIPT
from tests.test_summaries import _summary_json
from tube_agent.models.schemas import ChannelCreate
from tube_agent.services import pipeline
from tube_agent.services.transcripts import TranscriptResult, TranscriptUnavailableError


CHANNEL_RAW = {
    "id": "UC_pipeline",
    "snippet": {
        "title": "Pipeline Channel",
        "description": "Useful videos for testing.",
        "country": "US",
        "publishedAt": "2020-01-01T00:00:00Z",
    },
    "statistics": {
        "subscriberCount": "1234",
        "viewCount": "98765",
        "videoCount": "2",
    },
    "contentDetails": {
        "relatedPlaylists": {
            "uploads": "UU_pipeline",
        },
    },
}

VIDEO_DETAILS = [
    {
        "id": "vid_a",
        "snippet": {
            "title": "First pipeline video",
            "description": "Video A",
            "publishedAt": "2024-01-15T00:00:00Z",
            "tags": ["pipeline", "transcript"],
            "categoryId": "22",
        },
        "statistics": {
            "viewCount": "1000",
            "likeCount": "100",
            "commentCount": "10",
        },
        "contentDetails": {"duration": "PT1M30S"},
    },
    {
        "id": "vid_b",
        "snippet": {
            "title": "Second pipeline video",
            "description": "Video B",
            "publishedAt": "2024-01-16T00:00:00Z",
            "tags": ["pipeline"],
            "categoryId": "22",
        },
        "statistics": {
            "viewCount": "2000",
            "likeCount": "300",
            "commentCount": "20",
        },
        "contentDetails": {"duration": "PT2M"},
    },
]


class FakeQuota:
    def summary(self):
        return "Quota used: fake"


class FakeYouTubeClient:
    closed = False

    def __init__(self, api_key):
        self.api_key = api_key
        self.quota = FakeQuota()

    def get_channel_by_handle(self, handle):
        return CHANNEL_RAW

    def get_uploads_playlist_items(self, playlist_id, max_results=100):
        return [
            {"snippet": {"resourceId": {"videoId": video["id"]}}}
            for video in VIDEO_DETAILS[:max_results]
        ]

    def get_video_details(self, video_ids):
        wanted = set(video_ids)
        return [video for video in VIDEO_DETAILS if video["id"] in wanted]

    def close(self):
        self.__class__.closed = True


class SuccessfulTranscriptExtractor:
    seen = []

    def __init__(self, languages):
        self.languages = languages

    def extract(self, video_id):
        self.__class__.seen.append(video_id)
        return TranscriptResult(
            video_id=video_id,
            language="en",
            source="manual",
            segments=SAMPLE_TRANSCRIPT,
        )


class RateLimitedTranscriptExtractor:
    seen = []

    def __init__(self, languages):
        self.languages = languages

    def extract(self, video_id):
        self.__class__.seen.append(video_id)
        raise TranscriptUnavailableError(
            "YouTube transcript endpoint rate-limited this device/network (HTTP 429)"
        )


class FakeEmbedder:
    name = "fake:test"
    dimension = 3

    def embed(self, texts):
        return [np.array([1.0, 0.0, 0.0], dtype=np.float32) for _ in texts]


class FakeGeminiClient:
    prompts = []

    def __init__(self, api_key):
        self.api_key = api_key

    def generate_text(self, prompt):
        self.__class__.prompts.append(prompt)
        if "Based on the data below" in prompt:
            return "# Channel overview\n\nStart here."
        return _summary_json()

    def summary(self):
        return "Fake Gemini"


def _seed_channel_and_videos(storage):
    storage.save_channel(
        {
            "id": CHANNEL_RAW["id"],
            "handle": "pipeline",
            "title": "Pipeline Channel",
            "description": "Useful videos for testing.",
            "country": "US",
            "subscriber_count": 1234,
            "view_count": 98765,
            "video_count": 2,
            "published_at": "2020-01-01T00:00:00Z",
            "raw_json": CHANNEL_RAW,
        }
    )
    return pipeline.fetch_videos(FakeYouTubeClient("yt-key"), CHANNEL_RAW | {"uploadsPlaylistId": "UU_pipeline"}, 2, storage)


def test_fetch_channel_and_videos_save_normalized_metadata(storage):
    client = FakeYouTubeClient("yt-key")

    channel = pipeline.fetch_channel(client, "pipeline", storage)
    videos = pipeline.fetch_videos(client, channel, 2, storage)

    stored_channel = storage.get_channel("pipeline")
    assert stored_channel["id"] == "UC_pipeline"
    assert stored_channel["subscriber_count"] == 1234

    stored_videos, total = storage.list_videos("UC_pipeline", sort_by="published_at", sort_order="asc")
    assert total == 2
    assert videos[0]["durationSeconds"] == 90
    assert stored_videos[0]["video_id"] == "vid_a"
    assert stored_videos[1]["view_count"] == 2000


def test_fetch_transcripts_saves_segments_and_skips_existing(storage, monkeypatch):
    from tube_agent.services import transcripts as transcripts_module

    monkeypatch.setattr(transcripts_module, "TranscriptExtractor", SuccessfulTranscriptExtractor)
    monkeypatch.setattr(pipeline.time, "sleep", lambda *_: None)
    SuccessfulTranscriptExtractor.seen = []
    videos = _seed_channel_and_videos(storage)
    storage.save_transcript_segments("vid_a", "en", "manual", SAMPLE_TRANSCRIPT)

    results = pipeline.fetch_transcripts(videos, storage, ["ko", "en"], max_workers=1)

    assert results == {"vid_a": True, "vid_b": True}
    assert SuccessfulTranscriptExtractor.seen == ["vid_b"]
    assert len(storage.get_transcript("vid_b")) == 2


def test_fetch_transcripts_records_rate_limit_and_stops_sequential_fetch(storage, monkeypatch):
    from tube_agent.services import transcripts as transcripts_module

    monkeypatch.setattr(transcripts_module, "TranscriptExtractor", RateLimitedTranscriptExtractor)
    monkeypatch.setattr(pipeline.time, "sleep", lambda *_: None)
    RateLimitedTranscriptExtractor.seen = []
    videos = _seed_channel_and_videos(storage)
    failures = {}

    results = pipeline.fetch_transcripts(
        videos,
        storage,
        ["ko", "en"],
        max_workers=1,
        failure_notes=failures,
    )

    assert results == {"vid_a": False, "vid_b": False}
    assert RateLimitedTranscriptExtractor.seen == ["vid_a"]
    assert "HTTP 429" in failures["vid_a"]
    assert "HTTP 429" in failures["vid_b"]
    assert storage.get_transcript("vid_a") == []
    assert storage.get_transcript("vid_b") == []


def test_run_full_pipeline_orchestrates_index_embed_summary_and_report(storage, monkeypatch):
    from tube_agent.services import transcripts as transcripts_module

    monkeypatch.setattr(pipeline, "YouTubeClient", FakeYouTubeClient)
    monkeypatch.setattr(pipeline, "GeminiClient", FakeGeminiClient)
    monkeypatch.setattr(transcripts_module, "TranscriptExtractor", SuccessfulTranscriptExtractor)
    monkeypatch.setattr(pipeline.time, "sleep", lambda *_: None)
    FakeYouTubeClient.closed = False
    FakeGeminiClient.prompts = []
    SuccessfulTranscriptExtractor.seen = []

    result = pipeline.run_full_pipeline(
        handle="pipeline",
        storage=storage,
        youtube_api_key="yt-key",
        gemini_api_key="gemini-key",
        max_videos=2,
        skip_summaries=False,
        fetch_transcript_data=True,
        summary_max=2,
        skip_report=False,
        embedder=FakeEmbedder(),
    )

    assert result["channel_id"] == "UC_pipeline"
    assert result["video_count"] == 2
    assert result["transcript_count"] == 2
    assert result["transcript_failure_count"] == 0
    assert result["embedded_count"] == 4
    assert result["summary_count"] == 2
    assert result["report_generated"] is True
    assert FakeYouTubeClient.closed is True

    assert len(storage.get_transcript("vid_a")) == 2
    assert storage.get_summary("vid_a")["summary_intro"].startswith("This video explains")
    assert storage.get_report("UC_pipeline", "channel_overview")["content_md"].startswith("# Channel overview")


def test_run_full_pipeline_surfaces_transcript_failures_without_summaries(storage, monkeypatch):
    from tube_agent.services import transcripts as transcripts_module

    monkeypatch.setattr(pipeline, "YouTubeClient", FakeYouTubeClient)
    monkeypatch.setattr(transcripts_module, "TranscriptExtractor", RateLimitedTranscriptExtractor)
    monkeypatch.setattr(pipeline.time, "sleep", lambda *_: None)
    RateLimitedTranscriptExtractor.seen = []

    result = pipeline.run_full_pipeline(
        handle="pipeline",
        storage=storage,
        youtube_api_key="yt-key",
        gemini_api_key="",
        max_videos=2,
        skip_summaries=True,
        fetch_transcript_data=True,
        skip_report=True,
        embedder=FakeEmbedder(),
    )

    assert result["transcript_count"] == 0
    assert result["transcript_failure_count"] == 2
    assert result["embedded_count"] == 0
    assert "HTTP 429" in result["transcript_failures"]["vid_a"]


def test_background_pipeline_job_marks_completed_with_progress(storage, monkeypatch):
    from tube_agent.api.routes import channels as channels_route

    class Settings:
        youtube_api_key = "yt-key"
        gemini_api_key = "gemini-key"

    def fake_pipeline(**kwargs):
        assert kwargs["embedder"] == "embedder"
        return {
            "channel_id": "UC_pipeline",
            "handle": kwargs["handle"],
            "video_count": 2,
            "transcript_count": 2,
            "transcript_failure_count": 0,
            "summary_count": 1,
            "embedded_count": 4,
            "report_generated": False,
            "quota": "Quota used: fake",
        }

    monkeypatch.setattr(channels_route, "get_settings", lambda: Settings())
    monkeypatch.setattr(channels_route, "wait_for_embedding_ready", lambda timeout: True)
    monkeypatch.setattr(channels_route, "get_default_provider", lambda: "embedder")
    monkeypatch.setattr(channels_route, "run_full_pipeline", fake_pipeline)

    job_id = storage.create_job({"job_type": "full_pipeline", "config": {"handle": "pipeline"}})
    channels_route._run_pipeline_job(
        job_id,
        "pipeline",
        ChannelCreate(handle="pipeline", fetch_transcripts=True, skip_summaries=False),
        storage,
    )

    job = storage.get_job(job_id)
    assert job["status"] == "completed"
    assert job["channel_id"] == "UC_pipeline"
    assert job["progress"]["transcript_count"] == 2
    assert job["progress"]["summary_count"] == 1


def test_background_pipeline_job_marks_failed_on_exception(storage, monkeypatch):
    from tube_agent.api.routes import channels as channels_route

    class Settings:
        youtube_api_key = "yt-key"
        gemini_api_key = ""

    def failing_pipeline(**kwargs):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(channels_route, "get_settings", lambda: Settings())
    monkeypatch.setattr(channels_route, "run_full_pipeline", failing_pipeline)

    job_id = storage.create_job({"job_type": "full_pipeline", "config": {"handle": "pipeline"}})
    channels_route._run_pipeline_job(
        job_id,
        "pipeline",
        ChannelCreate(handle="pipeline", fetch_transcripts=False),
        storage,
    )

    job = storage.get_job(job_id)
    assert job["status"] == "failed"
    assert job["error"] == "pipeline exploded"
