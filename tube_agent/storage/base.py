"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """Abstract interface for data persistence."""

    def create_tables(self) -> None:
        """Create database tables. No-op for non-DB backends."""
        pass

    def get_session(self):
        """Get a database session. Only meaningful for DB backends."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support get_session(). "
            "Use PostgresStorage for session-based operations."
        )

    # --- Channel ---

    @abstractmethod
    def save_channel(self, data: dict) -> str:
        """Save channel data. Returns channel ID."""
        ...

    @abstractmethod
    def get_channel(self, handle: str) -> dict | None:
        """Get channel by handle."""
        ...

    @abstractmethod
    def list_channels(self, offset: int = 0, limit: int = 50) -> tuple[list[dict], int]:
        """List channels with pagination. Returns (channels, total_count)."""
        ...

    # --- Videos ---

    @abstractmethod
    def save_videos(self, channel_id: str, videos: list[dict]) -> int:
        """Save video list for a channel. Returns count saved."""
        ...

    @abstractmethod
    def get_video(self, video_id: str) -> dict | None:
        """Get a single video by ID."""
        ...

    @abstractmethod
    def list_videos(
        self,
        channel_id: str,
        sort_by: str = "published_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """List videos for a channel with sorting and pagination."""
        ...

    # --- Comments ---

    @abstractmethod
    def save_comments(self, video_id: str, comments: list[dict]) -> int:
        """Save comments for a video. Returns count saved."""
        ...

    @abstractmethod
    def get_comments(self, video_id: str, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
        """Get comments for a video with pagination."""
        ...

    @abstractmethod
    def has_comments(self, video_id: str) -> bool:
        """Check if comments exist for a video."""
        ...

    # --- Summaries ---

    @abstractmethod
    def save_summary(self, video_id: str, title: str, analysis: dict) -> None:
        """Save a Gemini analysis summary for a video."""
        ...

    @abstractmethod
    def get_summary(self, video_id: str) -> dict | None:
        """Get summary for a video."""
        ...

    @abstractmethod
    def has_summary(self, video_id: str) -> bool:
        """Check if a summary exists for a video."""
        ...

    # --- Transcripts ---

    @abstractmethod
    def save_transcript_segments(self, video_id: str, language: str, source: str, segments: list[dict]) -> int:
        """Save transcript segments for a video/language. Returns count saved."""
        ...

    @abstractmethod
    def get_transcript(self, video_id: str, language: str | None = None) -> list[dict]:
        """Get transcript segments for a video."""
        ...

    @abstractmethod
    def has_transcript(self, video_id: str, language: str | None = None) -> bool:
        """Check if transcript segments exist for a video."""
        ...

    @abstractmethod
    def search_transcripts(self, q: str, limit: int = 20, channel_id: str | None = None) -> list[dict]:
        """Search transcript segments."""
        ...

    # --- Embeddings ---

    @abstractmethod
    def list_unembedded_segments(
        self, model_name: str, channel_id: str | None = None, limit: int | None = None
    ) -> list[dict]:
        """Return transcript segments that don't have an embedding for the given model."""
        ...

    @abstractmethod
    def save_embeddings(
        self, items: list[tuple[int, "list[float] | bytes"]], model_name: str, dimension: int
    ) -> int:
        """Save embeddings for a batch of (segment_id, vector) pairs. Returns count saved."""
        ...

    @abstractmethod
    def search_semantic(
        self,
        query_vector: "list[float]",
        model_name: str,
        limit: int = 20,
        channel_id: str | None = None,
    ) -> list[dict]:
        """Cosine-similarity search over stored embeddings; returns top-k segments with metadata."""
        ...

    # --- Reports ---

    @abstractmethod
    def save_report(self, channel_id: str, report_type: str, content_md: str, tenant_id: str | None = None) -> Any:
        """Save an analysis report."""
        ...

    @abstractmethod
    def get_report(self, channel_id: str, report_type: str, tenant_id: str | None = None) -> dict | None:
        """Get the latest report of a given type for a channel."""
        ...

    @abstractmethod
    def list_reports(self, channel_id: str, tenant_id: str | None = None) -> list[dict]:
        """List all reports for a channel."""
        ...

    # --- Jobs ---

    @abstractmethod
    def create_job(self, job_data: dict) -> str:
        """Create a new job. Returns job ID."""
        ...

    @abstractmethod
    def get_job(self, job_id: str) -> dict | None:
        """Get job by ID."""
        ...

    @abstractmethod
    def update_job(self, job_id: str, updates: dict) -> None:
        """Update job fields."""
        ...
