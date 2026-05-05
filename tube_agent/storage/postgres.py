"""PostgreSQL storage backend using SQLAlchemy."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, desc, asc, func, select
from sqlalchemy.orm import Session, sessionmaker


def _parse_dt(value: str | datetime | None) -> datetime | None:
    """Parse an ISO 8601 datetime string to a datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

from tube_agent.models.database import (
    Base,
    Channel,
    Video,
    Comment,
    VideoSummary,
    SummarySection,
    SummaryBullet,
    TranscriptSegment,
    ChannelReport,
    Job,
)
from tube_agent.storage.base import StorageBackend


class PostgresStorage(StorageBackend):
    """PostgreSQL storage backend."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    # --- Channel ---

    def save_channel(self, data: dict) -> str:
        with self.get_session() as session:
            channel = session.get(Channel, data["id"])
            if channel:
                for key in ("handle", "title", "description", "country",
                            "subscriber_count", "view_count", "video_count",
                            "published_at", "raw_json"):
                    if key in data:
                        setattr(channel, key, data[key])
                channel.updated_at = datetime.now(timezone.utc)
            else:
                channel = Channel(
                    id=data["id"],
                    handle=data.get("handle", ""),
                    title=data.get("title", ""),
                    description=data.get("description", ""),
                    country=data.get("country", ""),
                    subscriber_count=data.get("subscriber_count", 0),
                    view_count=data.get("view_count", 0),
                    video_count=data.get("video_count", 0),
                    published_at=_parse_dt(data.get("published_at")),
                    raw_json=data.get("raw_json", {}),
                )
                session.add(channel)
            session.commit()
            return channel.id

    def get_channel(self, handle: str) -> dict | None:
        with self.get_session() as session:
            channel = session.execute(
                select(Channel).where(Channel.handle == handle)
            ).scalar_one_or_none()
            if not channel:
                return None
            return _channel_to_dict(channel)

    def list_channels(self, offset: int = 0, limit: int = 50) -> tuple[list[dict], int]:
        with self.get_session() as session:
            total = session.execute(select(func.count(Channel.id))).scalar()
            channels = session.execute(
                select(Channel)
                .order_by(desc(Channel.subscriber_count))
                .offset(offset).limit(limit)
            ).scalars().all()
            return [_channel_to_dict(ch) for ch in channels], total

    # --- Videos ---

    def save_videos(self, channel_id: str, videos: list[dict]) -> int:
        if not videos:
            return 0
        with self.get_session() as session:
            count = 0
            for v in videos:
                existing = session.get(Video, v["videoId"])
                if existing:
                    for key, col in _VIDEO_FIELD_MAP.items():
                        if key in v:
                            setattr(existing, col, v[key])
                else:
                    video = Video(
                        video_id=v["videoId"],
                        channel_id=channel_id,
                        title=v.get("title", ""),
                        description=v.get("description", ""),
                        published_at=_parse_dt(v.get("publishedAt")),
                        tags=v.get("tags", []),
                        category_id=v.get("categoryId", ""),
                        duration_seconds=v.get("durationSeconds", 0),
                        view_count=v.get("viewCount", 0),
                        like_count=v.get("likeCount", 0),
                        comment_count=v.get("commentCount", 0),
                        like_ratio=v.get("likeRatio", 0.0),
                        comment_ratio=v.get("commentRatio", 0.0),
                    )
                    session.add(video)
                count += 1
            session.commit()
            return count

    def get_video(self, video_id: str) -> dict | None:
        with self.get_session() as session:
            video = session.get(Video, video_id)
            if not video:
                return None
            return _video_to_dict(video)

    def list_videos(
        self, channel_id: str, sort_by: str = "published_at",
        sort_order: str = "desc", offset: int = 0, limit: int = 50,
    ) -> tuple[list[dict], int]:
        with self.get_session() as session:
            total = session.execute(
                select(func.count(Video.video_id))
                .where(Video.channel_id == channel_id)
            ).scalar()

            sort_col = _VIDEO_SORT_MAP.get(sort_by, Video.published_at)
            order_fn = desc if sort_order == "desc" else asc

            videos = session.execute(
                select(Video)
                .where(Video.channel_id == channel_id)
                .order_by(order_fn(sort_col))
                .offset(offset).limit(limit)
            ).scalars().all()
            return [_video_to_dict(v) for v in videos], total

    # --- Comments ---

    def save_comments(self, video_id: str, comments: list[dict]) -> int:
        if not comments:
            return 0
        with self.get_session() as session:
            for c in comments:
                comment = Comment(
                    video_id=video_id,
                    author=c.get("author", ""),
                    text=c.get("text", ""),
                    like_count=c.get("likeCount", c.get("like_count", 0)),
                    published_at=_parse_dt(c.get("publishedAt", c.get("published_at"))),
                )
                session.add(comment)
            session.commit()
            return len(comments)

    def get_comments(self, video_id: str, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
        with self.get_session() as session:
            total = session.execute(
                select(func.count(Comment.id))
                .where(Comment.video_id == video_id)
            ).scalar()
            comments = session.execute(
                select(Comment)
                .where(Comment.video_id == video_id)
                .order_by(desc(Comment.like_count))
                .offset(offset).limit(limit)
            ).scalars().all()
            return [_comment_to_dict(c) for c in comments], total

    def has_comments(self, video_id: str) -> bool:
        with self.get_session() as session:
            return session.execute(
                select(func.count(Comment.id))
                .where(Comment.video_id == video_id)
            ).scalar() > 0

    # --- Summaries ---

    def save_summary(self, video_id: str, title: str, analysis: dict) -> None:
        with self.get_session() as session:
            existing = session.get(VideoSummary, video_id)
            if existing:
                existing.summary_intro = analysis.get("summary_intro")
                existing.topics = analysis.get("topics", [])
                existing.content_type = analysis.get("content_type")
                existing.target_audience = analysis.get("target_audience")
                existing.tone = analysis.get("tone")
                existing.mentions = analysis.get("mentions", [])
                existing.notable_quotes = analysis.get("notable_quotes", [])
                existing.raw_analysis = analysis
                # Delete old sections/bullets and re-insert
                session.execute(
                    SummarySection.__table__.delete().where(SummarySection.video_id == video_id)
                )
                session.execute(
                    SummaryBullet.__table__.delete().where(SummaryBullet.video_id == video_id)
                )
            else:
                summary = VideoSummary(
                    video_id=video_id,
                    summary_intro=analysis.get("summary_intro"),
                    topics=analysis.get("topics", []),
                    content_type=analysis.get("content_type"),
                    target_audience=analysis.get("target_audience"),
                    tone=analysis.get("tone"),
                    mentions=analysis.get("mentions", []),
                    notable_quotes=analysis.get("notable_quotes", []),
                    raw_analysis=analysis,
                )
                session.add(summary)

            for i, s in enumerate(analysis.get("sections", [])):
                session.add(SummarySection(
                    video_id=video_id,
                    timestamp=s.get("timestamp", ""),
                    title=s.get("title", ""),
                    content=s.get("content", ""),
                    sort_order=i,
                ))
            for i, b in enumerate(analysis.get("summary_bullets", [])):
                session.add(SummaryBullet(
                    video_id=video_id,
                    title=b.get("title", ""),
                    timestamp=b.get("timestamp", ""),
                    description=b.get("description", ""),
                    sort_order=i,
                ))
            session.commit()

    def get_summary(self, video_id: str) -> dict | None:
        with self.get_session() as session:
            summary = session.get(VideoSummary, video_id)
            if not summary:
                return None
            return _summary_to_dict(summary)

    def has_summary(self, video_id: str) -> bool:
        with self.get_session() as session:
            return session.get(VideoSummary, video_id) is not None

    # --- Transcripts ---

    def save_transcript_segments(self, video_id: str, language: str, source: str, segments: list[dict]) -> int:
        with self.get_session() as session:
            session.execute(
                TranscriptSegment.__table__.delete()
                .where(TranscriptSegment.video_id == video_id)
                .where(TranscriptSegment.language == language)
            )
            for i, segment in enumerate(segments):
                session.add(TranscriptSegment(
                    video_id=video_id,
                    language=language,
                    source=source,
                    start_seconds=float(segment.get("start_seconds", 0.0)),
                    end_seconds=float(segment.get("end_seconds", 0.0)),
                    text=segment.get("text", ""),
                    sort_order=i,
                ))
            session.commit()
            return len(segments)

    def get_transcript(self, video_id: str, language: str | None = None) -> list[dict]:
        with self.get_session() as session:
            query = select(TranscriptSegment).where(TranscriptSegment.video_id == video_id)
            if language:
                query = query.where(TranscriptSegment.language == language)
            query = query.order_by(TranscriptSegment.language, TranscriptSegment.sort_order)
            segments = session.execute(query).scalars().all()
            return [_transcript_segment_to_dict(s) for s in segments]

    def has_transcript(self, video_id: str, language: str | None = None) -> bool:
        with self.get_session() as session:
            query = select(func.count(TranscriptSegment.id)).where(TranscriptSegment.video_id == video_id)
            if language:
                query = query.where(TranscriptSegment.language == language)
            return session.execute(query).scalar() > 0

    def search_transcripts(self, q: str, limit: int = 20, channel_id: str | None = None) -> list[dict]:
        pattern = f"%{q}%"
        with self.get_session() as session:
            query = (
                select(TranscriptSegment, Video, Channel)
                .join(Video, TranscriptSegment.video_id == Video.video_id)
                .join(Channel, Video.channel_id == Channel.id)
                .where(TranscriptSegment.text.ilike(pattern))
            )
            if channel_id:
                query = query.where(Video.channel_id == channel_id)
            rows = session.execute(
                query
                .order_by(desc(Video.published_at), TranscriptSegment.start_seconds)
                .limit(limit)
            ).all()
            return [
                {
                    "video_id": segment.video_id,
                    "channel_id": video.channel_id,
                    "channel_handle": channel.handle,
                    "video_title": video.title,
                    "language": segment.language,
                    "source": segment.source,
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "text": segment.text,
                }
                for segment, video, channel in rows
            ]

    # --- Reports ---

    def save_report(self, channel_id: str, report_type: str, content_md: str, tenant_id: str | None = None) -> Any:
        with self.get_session() as session:
            report = ChannelReport(
                channel_id=channel_id,
                tenant_id=tenant_id,
                report_type=report_type,
                content_md=content_md,
            )
            session.add(report)
            session.commit()
            return report.id

    def get_report(self, channel_id: str, report_type: str, tenant_id: str | None = None) -> dict | None:
        with self.get_session() as session:
            query = (
                select(ChannelReport)
                .where(ChannelReport.channel_id == channel_id)
                .where(ChannelReport.report_type == report_type)
            )
            if tenant_id:
                query = query.where(ChannelReport.tenant_id == tenant_id)
            query = query.order_by(desc(ChannelReport.created_at)).limit(1)
            report = session.execute(query).scalar_one_or_none()
            if not report:
                return None
            return _report_to_dict(report)

    def list_reports(self, channel_id: str, tenant_id: str | None = None) -> list[dict]:
        with self.get_session() as session:
            query = (
                select(ChannelReport)
                .where(ChannelReport.channel_id == channel_id)
            )
            if tenant_id:
                query = query.where(ChannelReport.tenant_id == tenant_id)
            query = query.order_by(desc(ChannelReport.created_at))
            reports = session.execute(query).scalars().all()
            return [_report_to_dict(r) for r in reports]

    # --- Jobs ---

    def create_job(self, job_data: dict) -> str:
        with self.get_session() as session:
            job = Job(
                id=str(uuid.uuid4()),
                tenant_id=job_data.get("tenant_id"),
                channel_id=job_data.get("channel_id"),
                job_type=job_data.get("job_type", "full_pipeline"),
                status="pending",
                config=job_data.get("config", {}),
            )
            session.add(job)
            session.commit()
            return job.id

    def get_job(self, job_id: str) -> dict | None:
        with self.get_session() as session:
            job = session.get(Job, job_id)
            if not job:
                return None
            return _job_to_dict(job)

    def update_job(self, job_id: str, updates: dict) -> None:
        with self.get_session() as session:
            job = session.get(Job, job_id)
            if job:
                # Auto-set started_at when transitioning to running
                if updates.get("status") == "running" and job.started_at is None:
                    job.started_at = datetime.now(timezone.utc)
                for key, value in updates.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                session.commit()


# --- Helper converters ---

_VIDEO_FIELD_MAP = {
    "title": "title",
    "description": "description",
    "publishedAt": "published_at",
    "tags": "tags",
    "categoryId": "category_id",
    "durationSeconds": "duration_seconds",
    "viewCount": "view_count",
    "likeCount": "like_count",
    "commentCount": "comment_count",
    "likeRatio": "like_ratio",
    "commentRatio": "comment_ratio",
}

_VIDEO_SORT_MAP = {
    "published_at": Video.published_at,
    "view_count": Video.view_count,
    "like_count": Video.like_count,
    "comment_count": Video.comment_count,
    "duration_seconds": Video.duration_seconds,
}


def _channel_to_dict(ch: Channel) -> dict:
    return {
        "id": ch.id,
        "handle": ch.handle,
        "title": ch.title,
        "description": ch.description,
        "country": ch.country,
        "subscriber_count": ch.subscriber_count,
        "view_count": ch.view_count,
        "video_count": ch.video_count,
        "published_at": ch.published_at.isoformat() if ch.published_at else None,
        "fetched_at": ch.fetched_at.isoformat() if ch.fetched_at else None,
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
    }


def _video_to_dict(v: Video) -> dict:
    return {
        "video_id": v.video_id,
        "channel_id": v.channel_id,
        "title": v.title,
        "description": v.description,
        "published_at": v.published_at.isoformat() if v.published_at else None,
        "tags": v.tags or [],
        "category_id": v.category_id,
        "duration_seconds": v.duration_seconds,
        "view_count": v.view_count,
        "like_count": v.like_count,
        "comment_count": v.comment_count,
        "like_ratio": v.like_ratio,
        "comment_ratio": v.comment_ratio,
        "fetched_at": v.fetched_at.isoformat() if v.fetched_at else None,
        "has_summary": v.summary is not None,
    }


def _comment_to_dict(c: Comment) -> dict:
    return {
        "id": c.id,
        "video_id": c.video_id,
        "author": c.author,
        "text": c.text,
        "like_count": c.like_count,
        "published_at": c.published_at.isoformat() if c.published_at else None,
    }


def _format_timestamp(seconds: float | int | None) -> str:
    total = max(0, int(seconds or 0))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _transcript_segment_to_dict(s: TranscriptSegment) -> dict:
    return {
        "video_id": s.video_id,
        "language": s.language,
        "source": s.source,
        "start_seconds": s.start_seconds,
        "end_seconds": s.end_seconds,
        "timestamp": _format_timestamp(s.start_seconds),
        "text": s.text,
        "sort_order": s.sort_order,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _summary_to_dict(s: VideoSummary) -> dict:
    return {
        "video_id": s.video_id,
        "summary_intro": s.summary_intro,
        "topics": s.topics or [],
        "content_type": s.content_type,
        "target_audience": s.target_audience,
        "tone": s.tone,
        "mentions": s.mentions or [],
        "notable_quotes": s.notable_quotes or [],
        "sections": [
            {"timestamp": sec.timestamp, "title": sec.title, "content": sec.content}
            for sec in (s.sections or [])
        ],
        "bullets": [
            {"title": b.title, "timestamp": b.timestamp, "description": b.description}
            for b in (s.bullets or [])
        ],
        "raw_analysis": s.raw_analysis or {},
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _report_to_dict(r: ChannelReport) -> dict:
    return {
        "id": r.id,
        "channel_id": r.channel_id,
        "tenant_id": r.tenant_id,
        "report_type": r.report_type,
        "content_md": r.content_md,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _job_to_dict(j: Job) -> dict:
    return {
        "id": j.id,
        "tenant_id": j.tenant_id,
        "channel_id": j.channel_id,
        "job_type": j.job_type,
        "status": j.status,
        "progress": j.progress or {},
        "config": j.config or {},
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        "error": j.error,
    }
