"""Pydantic schemas for API request/response validation."""

import enum
from datetime import datetime

from pydantic import BaseModel, Field


# --- Enums ---

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, enum.Enum):
    FULL_PIPELINE = "full_pipeline"
    FETCH_CHANNEL = "fetch_channel"
    FETCH_VIDEOS = "fetch_videos"
    FETCH_COMMENTS = "fetch_comments"
    FETCH_SUMMARIES = "fetch_summaries"
    GENERATE_REPORT = "generate_report"


class ReportType(str, enum.Enum):
    CONTENT = "content_analysis"
    COMMENT = "comment_analysis"
    TREND = "trend_analysis"
    SUMMARY = "summary_analysis"
    FULL = "full_report"


# --- Channel ---

class ChannelCreate(BaseModel):
    handle: str = Field(..., description="YouTube channel handle (e.g. ycombinator)")
    max_videos: int = Field(default=100, ge=1, le=1000)
    skip_comments: bool = True
    skip_summaries: bool = True
    summary_max: int | None = None
    media_resolution: str = "low"
    fetch_transcripts: bool = True
    transcript_languages: list[str] = ["ko", "en"]


class ChannelResponse(BaseModel):
    id: str
    handle: str
    title: str
    description: str
    country: str
    subscriber_count: int
    view_count: int
    video_count: int
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChannelListResponse(BaseModel):
    channels: list[ChannelResponse]
    total: int


# --- Video ---

class VideoResponse(BaseModel):
    video_id: str
    channel_id: str
    title: str
    description: str
    published_at: datetime | None = None
    tags: list[str] = []
    category_id: str = ""
    duration_seconds: int = 0
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    like_ratio: float = 0.0
    comment_ratio: float = 0.0
    fetched_at: datetime | None = None
    has_summary: bool = False

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    videos: list[VideoResponse]
    total: int


# --- Comment ---

class CommentResponse(BaseModel):
    id: int
    video_id: str
    author: str
    text: str
    like_count: int = 0
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Summary ---

class SummarySectionResponse(BaseModel):
    timestamp: str
    title: str
    content: str

    model_config = {"from_attributes": True}


class SummaryBulletResponse(BaseModel):
    title: str
    timestamp: str
    description: str

    model_config = {"from_attributes": True}


class VideoSummaryResponse(BaseModel):
    video_id: str
    summary_intro: str | None = None
    topics: list[str] = []
    content_type: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    mentions: list[str] = []
    notable_quotes: list[str] = []
    sections: list[SummarySectionResponse] = []
    bullets: list[SummaryBulletResponse] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Transcripts ---

class TranscriptSegmentResponse(BaseModel):
    video_id: str
    language: str
    source: str
    start_seconds: float
    end_seconds: float
    timestamp: str
    text: str

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    video_id: str
    language: str | None = None
    segments: list[TranscriptSegmentResponse] = []


# --- Job ---

class JobCreate(BaseModel):
    channel_handle: str
    job_type: JobType = JobType.FULL_PIPELINE
    config: dict = {}


class JobResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    channel_id: str | None = None
    job_type: str
    status: JobStatus
    progress: dict = {}
    config: dict = {}
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


# --- Report ---

class ReportResponse(BaseModel):
    id: int
    channel_id: str
    tenant_id: str | None = None
    report_type: str
    content_md: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int


# --- Search ---

class SearchResult(BaseModel):
    type: str  # "video" | "summary" | "transcript"
    video_id: str
    title: str
    snippet: str
    score: float = 0.0
    channel_handle: str | None = None
    video_title: str | None = None
    start_seconds: float | None = None
    timestamp: str | None = None
    youtube_url: str | None = None
    language: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str
