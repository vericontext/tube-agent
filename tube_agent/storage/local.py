"""Local JSON file storage backend - preserves existing CLI behavior."""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tube_agent.storage.base import StorageBackend

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _format_timestamp(seconds: float | int | None) -> str:
    total = max(0, int(seconds or 0))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class LocalStorage(StorageBackend):
    """JSON file-based storage matching the original scripts/ behavior."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or BASE_DIR
        self._jobs: dict[str, dict] = {}
        self._channel_map: dict[str, str] = {}  # channel_id → handle
        self._lock = threading.Lock()

    def _paths(self, handle: str) -> dict[str, Path]:
        base = self.base_dir / "data" / handle
        return {
            "raw": base / "raw",
            "processed": base / "processed",
            "output": self.base_dir / "output" / handle,
        }

    def _ensure_dirs(self, handle: str):
        p = self._paths(handle)
        for d in [
            p["raw"], p["raw"] / "comments", p["raw"] / "summaries",
            p["raw"] / "transcripts",
            p["processed"], p["output"], p["output"] / "reports",
        ]:
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_json(path: Path) -> dict | list | None:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _save_json(data: dict | list, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- Channel ---

    def _resolve_handle(self, channel_id_or_handle: str) -> str:
        """Resolve a channel_id to its handle, falling back to the input."""
        return self._channel_map.get(channel_id_or_handle, channel_id_or_handle)

    def _find_handle_for_video(self, video_id: str) -> str | None:
        """Find which handle directory contains a given video."""
        # Check channel_map handles first, then scan all dirs
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return None
        # Prioritize known handles
        for handle in self._channel_map.values():
            d = data_dir / handle
            videos = self._load_json(d / "processed" / "videos_enriched.json")
            if videos and any(v.get("videoId") == video_id for v in videos):
                return handle
        # Fallback: scan all directories
        for d in data_dir.iterdir():
            if d.is_dir() and d.name not in self._channel_map.values():
                videos = self._load_json(d / "processed" / "videos_enriched.json")
                if videos and any(v.get("videoId") == video_id for v in videos):
                    return d.name
        # No matching channel found — return None to prevent data corruption
        return None

    def save_channel(self, data: dict) -> str:
        handle = data.get("handle", "")
        channel_id = data.get("id", "")
        if channel_id and handle:
            self._channel_map[channel_id] = handle
        self._ensure_dirs(handle)
        paths = self._paths(handle)
        if "raw_json" in data:
            self._save_json(data["raw_json"], paths["raw"] / "channel.json")
        summary = {k: v for k, v in data.items() if k != "raw_json"}
        self._save_json(summary, paths["processed"] / "channel_summary.json")
        return channel_id

    def get_channel(self, handle: str) -> dict | None:
        paths = self._paths(handle)
        return self._load_json(paths["processed"] / "channel_summary.json")

    def list_channels(self, offset: int = 0, limit: int = 50) -> tuple[list[dict], int]:
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return [], 0
        channels = []
        for d in sorted(data_dir.iterdir()):
            if d.is_dir():
                ch = self._load_json(d / "processed" / "channel_summary.json")
                if ch:
                    channels.append(ch)
        total = len(channels)
        return channels[offset:offset + limit], total

    # --- Videos ---

    def save_videos(self, channel_id: str, videos: list[dict]) -> int:
        if not videos:
            return 0
        handle = self._resolve_handle(channel_id)
        paths = self._paths(handle)
        self._ensure_dirs(handle)
        self._save_json(videos, paths["processed"] / "videos_enriched.json")
        return len(videos)

    def get_video(self, video_id: str) -> dict | None:
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return None
        for d in data_dir.iterdir():
            if d.is_dir():
                videos = self._load_json(d / "processed" / "videos_enriched.json")
                if videos:
                    for v in videos:
                        if v.get("videoId") == video_id:
                            return v
        return None

    def list_videos(
        self, channel_id: str, sort_by: str = "published_at",
        sort_order: str = "desc", offset: int = 0, limit: int = 50,
    ) -> tuple[list[dict], int]:
        handle = self._resolve_handle(channel_id)
        paths = self._paths(handle)
        videos = self._load_json(paths["processed"] / "videos_enriched.json") or []
        field_map = {
            "published_at": "publishedAt",
            "view_count": "viewCount",
            "like_count": "likeCount",
            "comment_count": "commentCount",
        }
        sort_field = field_map.get(sort_by, sort_by)
        videos.sort(key=lambda v: v.get(sort_field, 0), reverse=(sort_order == "desc"))
        total = len(videos)
        return videos[offset:offset + limit], total

    # --- Comments ---

    def save_comments(self, video_id: str, comments: list[dict]) -> int:
        handle = self._find_handle_for_video(video_id)
        if not handle:
            return 0
        out_path = self.base_dir / "data" / handle / "raw" / "comments" / f"{video_id}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_json({"videoId": video_id, "comments": comments}, out_path)
        return len(comments)

    def get_comments(self, video_id: str, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return [], 0
        for d in data_dir.iterdir():
            if d.is_dir():
                path = d / "raw" / "comments" / f"{video_id}.json"
                data = self._load_json(path)
                if data:
                    comments = data.get("comments", [])
                    total = len(comments)
                    return comments[offset:offset + limit], total
        return [], 0

    def has_comments(self, video_id: str) -> bool:
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return False
        for d in data_dir.iterdir():
            if d.is_dir() and (d / "raw" / "comments" / f"{video_id}.json").exists():
                return True
        return False

    # --- Summaries ---

    def save_summary(self, video_id: str, title: str, analysis: dict) -> None:
        with self._lock:
            handle = self._find_handle_for_video(video_id)
            if not handle:
                return
            out_path = self.base_dir / "data" / handle / "raw" / "summaries" / f"{video_id}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_json(
                {"videoId": video_id, "title": title, "analysis": analysis},
                out_path,
            )

    def get_summary(self, video_id: str) -> dict | None:
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return None
        for d in data_dir.iterdir():
            if d.is_dir():
                path = d / "raw" / "summaries" / f"{video_id}.json"
                data = self._load_json(path)
                if data and "analysis" in data:
                    return data
        return None

    def has_summary(self, video_id: str) -> bool:
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return False
        for d in data_dir.iterdir():
            if d.is_dir() and (d / "raw" / "summaries" / f"{video_id}.json").exists():
                return True
        return False

    # --- Transcripts ---

    def save_transcript_segments(self, video_id: str, language: str, source: str, segments: list[dict]) -> int:
        handle = self._find_handle_for_video(video_id)
        if not handle:
            return 0
        out_path = self.base_dir / "data" / handle / "raw" / "transcripts" / f"{video_id}.{language}.json"
        normalized = [
            {
                "video_id": video_id,
                "language": language,
                "source": source,
                "start_seconds": float(s.get("start_seconds", 0.0)),
                "end_seconds": float(s.get("end_seconds", 0.0)),
                "timestamp": _format_timestamp(s.get("start_seconds", 0.0)),
                "text": s.get("text", ""),
                "sort_order": i,
            }
            for i, s in enumerate(segments)
        ]
        self._save_json(
            {
                "videoId": video_id,
                "language": language,
                "source": source,
                "segments": normalized,
            },
            out_path,
        )
        return len(normalized)

    def get_transcript(self, video_id: str, language: str | None = None) -> list[dict]:
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return []
        segments = []
        for d in data_dir.iterdir():
            if not d.is_dir():
                continue
            transcript_dir = d / "raw" / "transcripts"
            if not transcript_dir.exists():
                continue
            pattern = f"{video_id}.{language}.json" if language else f"{video_id}.*.json"
            for path in sorted(transcript_dir.glob(pattern)):
                data = self._load_json(path)
                if data:
                    segments.extend(data.get("segments", []))
        return sorted(segments, key=lambda s: (s.get("language", ""), s.get("sort_order", 0)))

    def has_transcript(self, video_id: str, language: str | None = None) -> bool:
        return bool(self.get_transcript(video_id, language))

    def search_transcripts(self, q: str, limit: int = 20, channel_id: str | None = None) -> list[dict]:
        needle = q.lower()
        results = []
        data_dir = self.base_dir / "data"
        if not data_dir.exists():
            return []
        for d in data_dir.iterdir():
            if not d.is_dir():
                continue
            channel = self._load_json(d / "processed" / "channel_summary.json") or {}
            if channel_id and channel.get("id") != channel_id:
                continue
            videos = self._load_json(d / "processed" / "videos_enriched.json") or []
            video_by_id = {v.get("videoId"): v for v in videos}
            transcript_dir = d / "raw" / "transcripts"
            if not transcript_dir.exists():
                continue
            for path in sorted(transcript_dir.glob("*.json")):
                data = self._load_json(path)
                if not data:
                    continue
                video_id = data.get("videoId", "")
                video = video_by_id.get(video_id, {})
                for segment in data.get("segments", []):
                    text = segment.get("text", "")
                    if needle in text.lower():
                        results.append({
                            "video_id": video_id,
                            "channel_id": channel.get("id", ""),
                            "channel_handle": channel.get("handle", d.name),
                            "video_title": video.get("title", ""),
                            "language": segment.get("language", data.get("language", "")),
                            "source": segment.get("source", data.get("source", "")),
                            "start_seconds": segment.get("start_seconds", 0.0),
                            "end_seconds": segment.get("end_seconds", 0.0),
                            "text": text,
                        })
                        if len(results) >= limit:
                            return results
        return results

    # --- Embeddings (LocalStorage does not support semantic search) ---

    def list_unembedded_segments(
        self, model_name: str, channel_id: str | None = None, limit: int | None = None
    ) -> list[dict]:
        return []

    def save_embeddings(
        self, items: list[tuple[int, list[float] | bytes]], model_name: str, dimension: int
    ) -> int:
        return 0

    def search_semantic(
        self,
        query_vector: list[float],
        model_name: str,
        limit: int = 20,
        channel_id: str | None = None,
    ) -> list[dict]:
        return []

    # --- Reports ---

    def save_report(self, channel_id: str, report_type: str, content_md: str, tenant_id: str | None = None) -> Any:
        handle = self._resolve_handle(channel_id)
        paths = self._paths(handle)
        self._ensure_dirs(handle)
        report_path = paths["output"] / "reports" / f"{report_type}.md"
        report_path.write_text(content_md, encoding="utf-8")
        return str(report_path)

    def get_report(self, channel_id: str, report_type: str, tenant_id: str | None = None) -> dict | None:
        handle = self._resolve_handle(channel_id)
        paths = self._paths(handle)
        report_path = paths["output"] / "reports" / f"{report_type}.md"
        if report_path.exists():
            return {
                "channel_id": channel_id,
                "report_type": report_type,
                "content_md": report_path.read_text(encoding="utf-8"),
            }
        # Also check output root for non-report analysis files
        alt_path = paths["output"] / f"{report_type}.md"
        if alt_path.exists():
            return {
                "channel_id": channel_id,
                "report_type": report_type,
                "content_md": alt_path.read_text(encoding="utf-8"),
            }
        return None

    def list_reports(self, channel_id: str, tenant_id: str | None = None) -> list[dict]:
        handle = self._resolve_handle(channel_id)
        paths = self._paths(handle)
        reports = []
        for md_file in (paths["output"] / "reports").glob("*.md"):
            reports.append({
                "channel_id": channel_id,
                "report_type": md_file.stem,
                "content_md": md_file.read_text(encoding="utf-8"),
            })
        return reports

    # --- Jobs (in-memory for CLI mode) ---

    def create_job(self, job_data: dict) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "id": job_id,
            **job_data,
            "status": "pending",
            "progress": {},
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, updates: dict) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update(updates)
