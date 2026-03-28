"""Composite storage backend - fan-out writes to multiple backends."""

import logging
from typing import Any

from tube_agent.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class CompositeStorage(StorageBackend):
    """Fan-out writes to multiple backends, reads from primary."""

    def __init__(self, primary: StorageBackend, *secondaries: StorageBackend):
        self.primary = primary
        self.secondaries = list(secondaries)

    def create_tables(self) -> None:
        self.primary.create_tables()

    def get_session(self):
        return self.primary.get_session()

    def _write_all(self, method: str, *args, **kwargs) -> Any:
        """Call a write method on all backends, return primary's result."""
        result = getattr(self.primary, method)(*args, **kwargs)
        for backend in self.secondaries:
            try:
                getattr(backend, method)(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    "Secondary storage %s.%s failed: %s",
                    type(backend).__name__, method, e,
                )
        return result

    # --- Channel ---

    def save_channel(self, data: dict) -> str:
        return self._write_all("save_channel", data)

    def get_channel(self, handle: str) -> dict | None:
        return self.primary.get_channel(handle)

    def list_channels(self, offset: int = 0, limit: int = 50) -> tuple[list[dict], int]:
        return self.primary.list_channels(offset, limit)

    # --- Videos ---

    def save_videos(self, channel_id: str, videos: list[dict]) -> int:
        return self._write_all("save_videos", channel_id, videos)

    def get_video(self, video_id: str) -> dict | None:
        return self.primary.get_video(video_id)

    def list_videos(
        self, channel_id: str, sort_by: str = "published_at",
        sort_order: str = "desc", offset: int = 0, limit: int = 50,
    ) -> tuple[list[dict], int]:
        return self.primary.list_videos(channel_id, sort_by, sort_order, offset, limit)

    # --- Comments ---

    def save_comments(self, video_id: str, comments: list[dict]) -> int:
        return self._write_all("save_comments", video_id, comments)

    def get_comments(self, video_id: str, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
        return self.primary.get_comments(video_id, offset, limit)

    def has_comments(self, video_id: str) -> bool:
        return self.primary.has_comments(video_id)

    # --- Summaries ---

    def save_summary(self, video_id: str, title: str, analysis: dict) -> None:
        self._write_all("save_summary", video_id, title, analysis)

    def get_summary(self, video_id: str) -> dict | None:
        return self.primary.get_summary(video_id)

    def has_summary(self, video_id: str) -> bool:
        return self.primary.has_summary(video_id)

    # --- Reports ---

    def save_report(self, channel_id: str, report_type: str, content_md: str, tenant_id: str | None = None) -> Any:
        return self._write_all("save_report", channel_id, report_type, content_md, tenant_id=tenant_id)

    def get_report(self, channel_id: str, report_type: str, tenant_id: str | None = None) -> dict | None:
        return self.primary.get_report(channel_id, report_type, tenant_id)

    def list_reports(self, channel_id: str, tenant_id: str | None = None) -> list[dict]:
        return self.primary.list_reports(channel_id, tenant_id)

    # --- Jobs (primary only) ---

    def create_job(self, job_data: dict) -> str:
        return self.primary.create_job(job_data)

    def get_job(self, job_id: str) -> dict | None:
        return self.primary.get_job(job_id)

    def update_job(self, job_id: str, updates: dict) -> None:
        self.primary.update_job(job_id, updates)
