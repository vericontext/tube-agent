"""Channel API routes."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from tube_agent.api.deps import get_storage
from tube_agent.config import get_settings
from tube_agent.models.schemas import (
    ChannelCreate,
    ChannelResponse,
    ChannelListResponse,
    JobResponse,
)
from tube_agent.services.embeddings import get_default_provider
from tube_agent.services.pipeline import run_full_pipeline
from tube_agent.storage.postgres import PostgresStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["channels"])


def _run_pipeline_job(job_id: str, handle: str, body: ChannelCreate, storage: PostgresStorage) -> None:
    """Run the analysis pipeline in the background and update the job record."""
    settings = get_settings()
    storage.update_job(job_id, {"status": "running"})
    try:
        embedder = None
        if body.fetch_transcripts:
            try:
                embedder = get_default_provider()
            except Exception as e:
                logger.warning("Embedder unavailable, transcripts will not be embedded: %s", e)

        result = run_full_pipeline(
            handle=handle,
            storage=storage,
            youtube_api_key=settings.youtube_api_key,
            gemini_api_key=settings.gemini_api_key,
            max_videos=body.max_videos,
            skip_comments=body.skip_comments,
            skip_summaries=body.skip_summaries,
            fetch_transcript_data=body.fetch_transcripts,
            transcript_languages=body.transcript_languages,
            summary_max=body.summary_max,
            media_resolution=body.media_resolution,
            embedder=embedder,
        )
        storage.update_job(job_id, {
            "status": "completed",
            "channel_id": result["channel_id"],
            "progress": result,
        })
        logger.info("Pipeline completed for job %s", job_id)
    except Exception as e:
        logger.error("Pipeline failed for job %s: %s", job_id, e)
        storage.update_job(job_id, {"status": "failed", "error": str(e)})


@router.post("", response_model=JobResponse, status_code=202)
def create_channel_analysis(
    body: ChannelCreate,
    background_tasks: BackgroundTasks,
    storage: PostgresStorage = Depends(get_storage),
):
    """Start a new channel analysis pipeline. Returns a job to track progress."""
    handle = body.handle.lstrip("@")

    job_id = storage.create_job({
        "channel_id": None,
        "job_type": "full_pipeline",
        "config": {
            "handle": handle,
            "max_videos": body.max_videos,
            "skip_comments": body.skip_comments,
            "skip_summaries": body.skip_summaries,
            "fetch_transcripts": body.fetch_transcripts,
            "transcript_languages": body.transcript_languages,
            "summary_max": body.summary_max,
            "media_resolution": body.media_resolution,
        },
    })

    background_tasks.add_task(_run_pipeline_job, job_id, handle, body, storage)

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
