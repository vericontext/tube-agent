"""Search API routes."""

from fastapi import APIRouter, Depends, Query as QueryParam

from tube_agent.api.deps import get_storage
from tube_agent.models.schemas import SearchResponse, SearchResult
from tube_agent.storage.postgres import PostgresStorage
from tube_agent.models.database import Channel, Video, VideoSummary

from sqlalchemy import select, or_, cast, String

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = QueryParam(..., min_length=1, description="Search query"),
    type: str = QueryParam("all", pattern="^(all|videos|summaries|transcripts)$"),
    limit: int = QueryParam(20, ge=1, le=100),
    storage: PostgresStorage = Depends(get_storage),
):
    """Search across videos and summaries using PostgreSQL text search."""
    results = []
    pattern = f"%{q}%"

    with storage.get_session() as session:
        if type in ("all", "transcripts"):
            transcripts = storage.search_transcripts(q, limit)
            for segment in transcripts:
                video_id = segment["video_id"]
                start_seconds = segment.get("start_seconds", 0.0)
                results.append(SearchResult(
                    type="transcript",
                    video_id=video_id,
                    title=segment.get("video_title") or video_id,
                    snippet=segment.get("text", "")[:300],
                    channel_handle=segment.get("channel_handle"),
                    video_title=segment.get("video_title"),
                    start_seconds=start_seconds,
                    timestamp=_format_timestamp(start_seconds),
                    youtube_url=_youtube_url(video_id, start_seconds),
                    language=segment.get("language"),
                ))

        if type in ("all", "videos"):
            videos = session.execute(
                select(Video, Channel)
                .join(Channel, Video.channel_id == Channel.id)
                .where(or_(
                    Video.title.ilike(pattern),
                    Video.description.ilike(pattern),
                ))
                .limit(limit)
            ).all()
            for v, ch in videos:
                results.append(SearchResult(
                    type="video",
                    video_id=v.video_id,
                    title=v.title,
                    snippet=v.description[:200] if v.description else "",
                    channel_handle=ch.handle,
                    video_title=v.title,
                ))

        if type in ("all", "summaries"):
            # topics is stored as JSON text (StringListType), so cast to
            # String for LIKE matching instead of using .ilike() directly
            summaries = session.execute(
                select(VideoSummary, Video, Channel)
                .join(Video, VideoSummary.video_id == Video.video_id)
                .join(Channel, Video.channel_id == Channel.id)
                .where(or_(
                    VideoSummary.summary_intro.ilike(pattern),
                    cast(VideoSummary.topics, String).ilike(pattern),
                ))
                .limit(limit)
            ).all()
            for s, v, ch in summaries:
                results.append(SearchResult(
                    type="summary",
                    video_id=s.video_id,
                    title=v.title or ", ".join(s.topics or []),
                    snippet=s.summary_intro[:200] if s.summary_intro else "",
                    channel_handle=ch.handle,
                    video_title=v.title,
                ))

    return SearchResponse(results=results[:limit], total=len(results), query=q)


def _format_timestamp(seconds: float | int | None) -> str:
    total = max(0, int(seconds or 0))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _youtube_url(video_id: str, seconds: float | int | None) -> str:
    return f"https://www.youtube.com/watch?v={video_id}&t={max(0, int(seconds or 0))}s"
