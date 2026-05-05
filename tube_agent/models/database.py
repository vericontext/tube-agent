"""SQLAlchemy ORM models."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Float,
    LargeBinary,
    Text,
    DateTime,
    ForeignKey,
    Index,
    TypeDecorator,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# --- Portable types that work on both SQLite and PostgreSQL ---

class JSONType(TypeDecorator):
    """JSON column that works on both SQLite (as TEXT) and PostgreSQL (as JSONType)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


class StringListType(TypeDecorator):
    """List of strings stored as JSON text. Works on both SQLite and PostgreSQL."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return "[]"

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return []


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# --- Shared Data (tenant-independent) ---

class Channel(Base):
    __tablename__ = "channels"

    id = Column(String, primary_key=True)
    handle = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False, default="")
    description = Column(Text, default="")
    country = Column(String, default="")
    subscriber_count = Column(BigInteger, default=0)
    view_count = Column(BigInteger, default=0)
    video_count = Column(Integer, default=0)
    published_at = Column(DateTime(timezone=True))
    raw_json = Column(JSONType, default=dict)
    fetched_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")
    reports = relationship("ChannelReport", back_populates="channel", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_channels_subscriber_count", "subscriber_count"),
    )


class Video(Base):
    __tablename__ = "videos"

    video_id = Column(String, primary_key=True)
    channel_id = Column(String, ForeignKey("channels.id"), nullable=False)
    title = Column(String, nullable=False, default="")
    description = Column(Text, default="")
    published_at = Column(DateTime(timezone=True))
    tags = Column(StringListType, default=list)
    category_id = Column(String, default="")
    duration_seconds = Column(Integer, default=0)
    view_count = Column(BigInteger, default=0)
    like_count = Column(BigInteger, default=0)
    comment_count = Column(Integer, default=0)
    like_ratio = Column(Float, default=0.0)
    comment_ratio = Column(Float, default=0.0)
    fetched_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    channel = relationship("Channel", back_populates="videos")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")
    summary = relationship("VideoSummary", back_populates="video", uselist=False, cascade="all, delete-orphan")
    transcript_segments = relationship("TranscriptSegment", back_populates="video", cascade="all, delete-orphan",
                                       order_by="TranscriptSegment.sort_order")

    __table_args__ = (
        Index("ix_videos_channel_published", "channel_id", "published_at"),
        Index("ix_videos_channel_views", "channel_id", "view_count"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False)
    author = Column(String, default="")
    text = Column(Text, default="")
    like_count = Column(Integer, default=0)
    published_at = Column(DateTime(timezone=True))
    fetched_at = Column(DateTime(timezone=True), default=_utcnow)

    video = relationship("Video", back_populates="comments")

    __table_args__ = (
        Index("ix_comments_video_id", "video_id"),
    )


class VideoSummary(Base):
    __tablename__ = "video_summaries"

    video_id = Column(String, ForeignKey("videos.video_id"), primary_key=True)
    summary_intro = Column(Text)
    topics = Column(StringListType, default=list)
    content_type = Column(String)
    target_audience = Column(String)
    tone = Column(String)
    mentions = Column(StringListType, default=list)
    notable_quotes = Column(StringListType, default=list)
    raw_analysis = Column(JSONType, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    video = relationship("Video", back_populates="summary")
    sections = relationship("SummarySection", back_populates="summary", cascade="all, delete-orphan",
                            order_by="SummarySection.sort_order")
    bullets = relationship("SummaryBullet", back_populates="summary", cascade="all, delete-orphan",
                           order_by="SummaryBullet.sort_order")


class SummarySection(Base):
    __tablename__ = "summary_sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("video_summaries.video_id"), nullable=False)
    timestamp = Column(String, default="")
    title = Column(String, default="")
    content = Column(Text, default="")
    sort_order = Column(Integer, default=0)

    summary = relationship("VideoSummary", back_populates="sections")


class SummaryBullet(Base):
    __tablename__ = "summary_bullets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("video_summaries.video_id"), nullable=False)
    title = Column(String, default="")
    timestamp = Column(String, default="")
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)

    summary = relationship("VideoSummary", back_populates="bullets")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False)
    language = Column(String, default="")
    source = Column(String, default="")
    start_seconds = Column(Float, default=0.0)
    end_seconds = Column(Float, default=0.0)
    text = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    video = relationship("Video", back_populates="transcript_segments")
    embeddings = relationship("TranscriptEmbedding", back_populates="segment",
                              cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_transcript_segments_video_language", "video_id", "language"),
        Index("ix_transcript_segments_video_order", "video_id", "sort_order"),
    )


class TranscriptEmbedding(Base):
    __tablename__ = "transcript_embeddings"

    segment_id = Column(Integer, ForeignKey("transcript_segments.id"), primary_key=True)
    model_name = Column(String, primary_key=True)
    dimension = Column(Integer, nullable=False)
    embedding = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    segment = relationship("TranscriptSegment", back_populates="embeddings")

    __table_args__ = (
        Index("ix_transcript_embeddings_model", "model_name"),
    )


class ChannelReport(Base):
    __tablename__ = "channel_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String, ForeignKey("channels.id"), nullable=False)
    report_type = Column(String, nullable=False)
    content_md = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    channel = relationship("Channel", back_populates="reports")

    __table_args__ = (
        Index("ix_reports_channel_type", "channel_id", "report_type"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    channel_id = Column(String, ForeignKey("channels.id"))
    job_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    progress = Column(JSONType, default=dict)
    config = Column(JSONType, default=dict)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error = Column(Text)

    channel = relationship("Channel")

    __table_args__ = (
        Index("ix_jobs_status", "status"),
    )
