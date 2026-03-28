"""Channel API routes."""

import logging
import threading

from fastapi import APIRouter, Depends, HTTPException, Query

from tube_agent.api.auth import require_auth
from tube_agent.api.deps import get_storage
from tube_agent.models.schemas import (
    ChannelCreate,
    ChannelResponse,
    ChannelListResponse,
    JobResponse,
    JobStatus,
)
from tube_agent.storage.postgres import PostgresStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["channels"])

# Timeout for synchronous fallback (seconds)
_SYNC_FALLBACK_TIMEOUT = 120


@router.post("", response_model=JobResponse, status_code=202)
def create_channel_analysis(
    body: ChannelCreate,
    user: dict = Depends(require_auth),
    storage: PostgresStorage = Depends(get_storage),
):
    """Start a new channel analysis pipeline. Returns a job to track progress."""
    handle = body.handle.lstrip("@")

    job_id = storage.create_job({
        "channel_id": None,  # Will be set after channel fetch
        "job_type": "full_pipeline",
        "config": {
            "handle": handle,
            "max_videos": body.max_videos,
            "skip_comments": body.skip_comments,
            "skip_summaries": body.skip_summaries,
            "summary_max": body.summary_max,
            "media_resolution": body.media_resolution,
        },
    })

    # Dispatch Celery task
    try:
        from tube_agent.tasks.fetch import run_pipeline_task
        run_pipeline_task.delay(job_id, handle, body.model_dump())
        logger.info("Dispatched Celery task for job %s (handle=%s)", job_id, handle)
    except Exception as exc:
        # Celery not available or Redis unreachable — run in background thread
        # to avoid blocking the HTTP response indefinitely
        logger.warning("Celery dispatch failed (%s), running pipeline in background thread", exc)

        def _run_sync():
            from tube_agent.services.pipeline import run_full_pipeline
            from tube_agent.config import get_settings
            settings = get_settings()
            storage.update_job(job_id, {"status": "running"})
            try:
                result = run_full_pipeline(
                    handle=handle,
                    storage=storage,
                    youtube_api_key=settings.youtube_api_key,
                    gemini_api_key=settings.gemini_api_key,
                    max_videos=body.max_videos,
                    skip_comments=body.skip_comments,
                    skip_summaries=body.skip_summaries,
                    summary_max=body.summary_max,
                    media_resolution=body.media_resolution,
                )
                storage.update_job(job_id, {
                    "status": "completed",
                    "channel_id": result["channel_id"],
                    "progress": result,
                })
                logger.info("Sync fallback completed for job %s", job_id)
            except Exception as e:
                logger.error("Sync fallback failed for job %s: %s", job_id, e)
                storage.update_job(job_id, {"status": "failed", "error": str(e)})

        thread = threading.Thread(target=_run_sync, daemon=True)
        thread.start()

    job = storage.get_job(job_id)
    return JobResponse(**job)


@router.get("", response_model=ChannelListResponse)
def list_channels(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    storage: PostgresStorage = Depends(get_storage),
):
    """List all analyzed channels."""
    channels, total = storage.list_channels(offset=offset, limit=limit)
    return ChannelListResponse(
        channels=[ChannelResponse(**ch) for ch in channels],
        total=total,
    )


@router.get("/{handle}", response_model=ChannelResponse)
def get_channel(
    handle: str,
    storage: PostgresStorage = Depends(get_storage),
):
    """Get channel details by handle."""
    handle = handle.lstrip("@")
    channel = storage.get_channel(handle)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel @{handle} not found")
    return ChannelResponse(**channel)
