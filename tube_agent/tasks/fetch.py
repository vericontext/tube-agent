"""Celery tasks for data fetching pipeline."""

import logging
import threading
from datetime import datetime, timezone

from tube_agent.tasks.celery_app import celery_app
from tube_agent.config import get_settings
from tube_agent.storage.postgres import PostgresStorage
from tube_agent.storage.composite import CompositeStorage
from tube_agent.services.pipeline import run_full_pipeline

logger = logging.getLogger(__name__)

# Thread-safe singleton storage to prevent connection pool exhaustion
_storage_lock = threading.Lock()
_storage_instance = None


def _build_storage(settings=None):
    """Build or return singleton storage backend."""
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance
    with _storage_lock:
        if _storage_instance is not None:
            return _storage_instance
        if settings is None:
            settings = get_settings()
        pg = PostgresStorage(settings.database_url)
        if settings.r2_endpoint and settings.r2_access_key:
            from tube_agent.storage.r2 import R2Storage
            r2 = R2Storage(
                endpoint_url=settings.r2_endpoint,
                access_key=settings.r2_access_key,
                secret_key=settings.r2_secret_key,
                bucket=settings.r2_bucket,
            )
            _storage_instance = CompositeStorage(pg, r2)
        else:
            _storage_instance = pg
        return _storage_instance


@celery_app.task(name="tube_agent.tasks.fetch.run_pipeline_task", bind=True)
def run_pipeline_task(self, job_id: str, handle: str, config: dict):
    """Run the full channel analysis pipeline as a Celery task."""
    settings = get_settings()
    storage = _build_storage(settings)

    storage.update_job(job_id, {"status": "running"})

    try:
        result = run_full_pipeline(
            handle=handle,
            storage=storage,
            youtube_api_key=settings.youtube_api_key,
            gemini_api_key=settings.gemini_api_key,
            max_videos=config.get("max_videos", 100),
            skip_comments=config.get("skip_comments", False),
            skip_summaries=config.get("skip_summaries", False),
            summary_max=config.get("summary_max"),
            media_resolution=config.get("media_resolution", "low"),
            skip_report=config.get("skip_report", False),
        )
        storage.update_job(job_id, {
            "status": "completed",
            "channel_id": result["channel_id"],
            "progress": result,
            "completed_at": datetime.now(timezone.utc),
        })
        return result
    except Exception as e:
        storage.update_job(job_id, {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(timezone.utc),
        })
        raise


@celery_app.task(name="tube_agent.tasks.fetch.fetch_channel_task")
def fetch_channel_task(handle: str):
    """Fetch channel metadata only."""
    settings = get_settings()
    storage = _build_storage(settings)
    from tube_agent.services.youtube import YouTubeClient
    from tube_agent.services.pipeline import fetch_channel

    yt = YouTubeClient(settings.youtube_api_key)
    try:
        return fetch_channel(yt, handle, storage)
    finally:
        yt.close()


@celery_app.task(name="tube_agent.tasks.fetch.fetch_videos_task")
def fetch_videos_task(channel_data: dict, max_videos: int = 100):
    """Fetch videos for a channel."""
    settings = get_settings()
    storage = _build_storage(settings)
    from tube_agent.services.youtube import YouTubeClient
    from tube_agent.services.pipeline import fetch_videos

    yt = YouTubeClient(settings.youtube_api_key)
    try:
        videos = fetch_videos(yt, channel_data, max_videos, storage)
        return [v for v in videos]  # Ensure serializable
    finally:
        yt.close()


@celery_app.task(name="tube_agent.tasks.fetch.fetch_comments_task")
def fetch_comments_task(videos: list[dict]):
    """Fetch comments for videos."""
    settings = get_settings()
    storage = _build_storage(settings)
    from tube_agent.services.youtube import YouTubeClient
    from tube_agent.services.pipeline import fetch_comments

    yt = YouTubeClient(settings.youtube_api_key)
    try:
        fetch_comments(yt, videos, storage)
    finally:
        yt.close()


@celery_app.task(name="tube_agent.tasks.fetch.fetch_summaries_task")
def fetch_summaries_task(videos: list[dict], max_videos: int | None = None, media_resolution: str = "low"):
    """Analyze videos with Gemini."""
    settings = get_settings()
    storage = _build_storage(settings)
    from tube_agent.services.gemini import GeminiClient
    from tube_agent.services.pipeline import fetch_summaries

    gemini = GeminiClient(settings.gemini_api_key)
    return fetch_summaries(videos, storage, gemini, max_videos, media_resolution)
