"""Search API routes."""

from fastapi import APIRouter, Depends, Query as QueryParam

from tube_agent.api.deps import get_storage
from tube_agent.models.schemas import SearchResponse, SearchResult
from tube_agent.storage.postgres import PostgresStorage
from tube_agent.models.database import Video, VideoSummary

from sqlalchemy import select, or_, func, cast, String

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = QueryParam(..., min_length=1, description="Search query"),
    type: str = QueryParam("all", pattern="^(all|videos|summaries)$"),
    limit: int = QueryParam(20, ge=1, le=100),
    storage: PostgresStorage = Depends(get_storage),
):
    """Search across videos and summaries using PostgreSQL text search."""
    results = []
    pattern = f"%{q}%"

    with storage.get_session() as session:
        if type in ("all", "videos"):
            videos = session.execute(
                select(Video)
                .where(or_(
                    Video.title.ilike(pattern),
                    Video.description.ilike(pattern),
                ))
                .limit(limit)
            ).scalars().all()
            for v in videos:
                results.append(SearchResult(
                    type="video",
                    video_id=v.video_id,
                    title=v.title,
                    snippet=v.description[:200] if v.description else "",
                ))

        if type in ("all", "summaries"):
            # topics is stored as JSON text (StringListType), so cast to
            # String for LIKE matching instead of using .ilike() directly
            summaries = session.execute(
                select(VideoSummary)
                .where(or_(
                    VideoSummary.summary_intro.ilike(pattern),
                    cast(VideoSummary.topics, String).ilike(pattern),
                ))
                .limit(limit)
            ).scalars().all()
            for s in summaries:
                results.append(SearchResult(
                    type="summary",
                    video_id=s.video_id,
                    title=", ".join(s.topics or []),
                    snippet=s.summary_intro[:200] if s.summary_intro else "",
                ))

    return SearchResponse(results=results[:limit], total=len(results), query=q)
