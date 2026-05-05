"""Video and Summary API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from tube_agent.config import get_settings
from tube_agent.api.deps import get_storage
from tube_agent.models.schemas import (
    VideoResponse,
    VideoListResponse,
    VideoSummaryResponse,
    SummarySectionResponse,
    SummaryBulletResponse,
    SummaryGenerateRequest,
    TranscriptResponse,
    TranscriptFetchRequest,
    TranscriptSegmentResponse,
)
from tube_agent.services.embeddings import get_default_provider
from tube_agent.services.gemini import GeminiClient
from tube_agent.services.pipeline import embed_transcripts
from tube_agent.services.summaries import SummaryGenerationError, generate_and_save_transcript_summary
from tube_agent.services.transcripts import TranscriptExtractor, TranscriptUnavailableError
from tube_agent.storage.postgres import PostgresStorage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["videos"])


@router.get(
    "/channels/{handle}/videos",
    response_model=VideoListResponse,
)
def list_videos(
    handle: str,
    sort_by: str = Query("published_at", pattern="^(published_at|view_count|like_count|comment_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    storage: PostgresStorage = Depends(get_storage),
):
    """List videos for a channel with sorting and pagination."""
    handle = handle.lstrip("@")
    channel = storage.get_channel(handle)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel @{handle} not found")

    videos, total = storage.list_videos(
        channel_id=channel["id"],
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
        limit=limit,
    )
    return VideoListResponse(
        videos=[VideoResponse(**v) for v in videos],
        total=total,
    )


@router.get(
    "/channels/{handle}/videos/{video_id}",
    response_model=VideoResponse,
)
def get_video(
    handle: str,
    video_id: str,
    storage: PostgresStorage = Depends(get_storage),
):
    """Get a single video by ID."""
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    return VideoResponse(**video)


@router.get(
    "/channels/{handle}/videos/{video_id}/summary",
    response_model=VideoSummaryResponse,
)
def get_video_summary(
    handle: str,
    video_id: str,
    storage: PostgresStorage = Depends(get_storage),
):
    """Get the Gemini analysis summary for a video."""
    summary = storage.get_summary(video_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Summary not found for video {video_id}")

    return VideoSummaryResponse(
        video_id=summary["video_id"],
        summary_intro=summary.get("summary_intro"),
        topics=summary.get("topics", []),
        content_type=summary.get("content_type"),
        target_audience=summary.get("target_audience"),
        tone=summary.get("tone"),
        mentions=summary.get("mentions", []),
        notable_quotes=summary.get("notable_quotes", []),
        sections=[SummarySectionResponse(**s) for s in summary.get("sections", [])],
        bullets=[SummaryBulletResponse(**b) for b in summary.get("bullets", [])],
        created_at=summary.get("created_at"),
    )


@router.post(
    "/channels/{handle}/videos/{video_id}/summary",
    response_model=VideoSummaryResponse,
)
def generate_video_summary(
    handle: str,
    video_id: str,
    body: SummaryGenerateRequest | None = None,
    storage: PostgresStorage = Depends(get_storage),
):
    """Generate a transcript-backed summary for one video."""
    body = body or SummaryGenerateRequest()
    if body.summary_mode != "transcript":
        raise HTTPException(status_code=400, detail="Only transcript summary mode is supported by this endpoint")

    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is not configured")

    try:
        summary = generate_and_save_transcript_summary(
            storage,
            video_id,
            GeminiClient(settings.gemini_api_key),
            language=body.summary_language,
        )
    except SummaryGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return VideoSummaryResponse(
        video_id=summary["video_id"],
        summary_intro=summary.get("summary_intro"),
        topics=summary.get("topics", []),
        content_type=summary.get("content_type"),
        target_audience=summary.get("target_audience"),
        tone=summary.get("tone"),
        mentions=summary.get("mentions", []),
        notable_quotes=summary.get("notable_quotes", []),
        sections=[SummarySectionResponse(**s) for s in summary.get("sections", [])],
        bullets=[SummaryBulletResponse(**b) for b in summary.get("bullets", [])],
        created_at=summary.get("created_at"),
    )


@router.get(
    "/channels/{handle}/videos/{video_id}/transcript",
    response_model=TranscriptResponse,
)
def get_video_transcript(
    handle: str,
    video_id: str,
    language: str | None = Query(None, min_length=2),
    storage: PostgresStorage = Depends(get_storage),
):
    """Get transcript segments for a video."""
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    segments = storage.get_transcript(video_id, language)
    response_language = language
    if response_language is None and segments:
        response_language = segments[0].get("language")
    return TranscriptResponse(
        video_id=video_id,
        language=response_language,
        segments=[TranscriptSegmentResponse(**s) for s in segments],
    )


@router.post(
    "/channels/{handle}/videos/{video_id}/transcript",
    response_model=TranscriptResponse,
)
def fetch_video_transcript(
    handle: str,
    video_id: str,
    body: TranscriptFetchRequest | None = None,
    storage: PostgresStorage = Depends(get_storage),
):
    """Fetch or retry transcript capture for one stored video."""
    body = body or TranscriptFetchRequest()
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    languages = body.languages or ["ko", "en"]
    try:
        transcript = TranscriptExtractor(languages).extract(video_id)
    except TranscriptUnavailableError as e:
        status_code = 429 if "HTTP 429" in str(e) or "rate-limited" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e)) from e

    storage.save_transcript_segments(
        transcript.video_id,
        transcript.language,
        transcript.source,
        transcript.segments,
    )

    if body.embed:
        try:
            embedder = get_default_provider()
            embed_transcripts(storage, embedder, channel_id=video.get("channel_id"))
        except Exception as e:
            logger.warning("Embedding after transcript retry failed for %s: %s", video_id, e)

    segments = storage.get_transcript(video_id, transcript.language)
    return TranscriptResponse(
        video_id=video_id,
        language=transcript.language,
        segments=[TranscriptSegmentResponse(**s) for s in segments],
    )
