"""Cloudflare R2 (S3-compatible) storage backend."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from tube_agent.storage.base import StorageBackend


class R2Storage(StorageBackend):
    """S3-compatible object storage backend for Cloudflare R2."""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        self._jobs: dict[str, dict] = {}
        self._channel_map: dict[str, str] = {}  # channel_id → handle

    def _key(self, *parts: str) -> str:
        return "/".join(parts)

    def _put_json(self, key: str, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=body.encode("utf-8"), ContentType="application/json")

    def _get_json(self, key: str) -> Any | None:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
            return json.loads(resp["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def _head(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def _resolve_handle(self, channel_id_or_handle: str) -> str:
        return self._channel_map.get(channel_id_or_handle, channel_id_or_handle)

    # --- Channel ---

    def save_channel(self, data: dict) -> str:
        handle = data.get("handle", "")
        channel_id = data.get("id", "")
        if channel_id and handle:
            self._channel_map[channel_id] = handle
        self._put_json(self._key("channels", handle, "channel.json"), data)
        return channel_id

    def get_channel(self, handle: str) -> dict | None:
        return self._get_json(self._key("channels", handle, "channel.json"))

    def list_channels(self, offset: int = 0, limit: int = 50) -> tuple[list[dict], int]:
        # List channel prefixes by scanning for channel.json files
        paginator = self.client.get_paginator("list_objects_v2")
        channels = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix="channels/", Delimiter="/"):
            for prefix in page.get("CommonPrefixes", []):
                handle = prefix["Prefix"].split("/")[1]
                ch = self._get_json(self._key("channels", handle, "channel.json"))
                if ch:
                    channels.append(ch)
        total = len(channels)
        return channels[offset:offset + limit], total

    # --- Videos ---

    def save_videos(self, channel_id: str, videos: list[dict]) -> int:
        if not videos:
            return 0
        handle = self._resolve_handle(channel_id)
        self._put_json(self._key("channels", handle, "videos.json"), videos)
        return len(videos)

    def get_video(self, video_id: str) -> dict | None:
        # Search across known handles
        for handle in self._channel_map.values():
            videos = self._get_json(self._key("channels", handle, "videos.json"))
            if videos:
                for v in videos:
                    if v.get("videoId") == video_id:
                        return v
        return None

    def list_videos(
        self,
        channel_id: str,
        sort_by: str = "published_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        handle = self._resolve_handle(channel_id)
        videos = self._get_json(self._key("channels", handle, "videos.json")) or []
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
        self._put_json(
            self._key("channels", handle, "comments", f"{video_id}.json"),
            {"videoId": video_id, "comments": comments},
        )
        return len(comments)

    def get_comments(self, video_id: str, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
        for handle in self._channel_map.values():
            data = self._get_json(self._key("channels", handle, "comments", f"{video_id}.json"))
            if data:
                comments = data.get("comments", [])
                total = len(comments)
                return comments[offset:offset + limit], total
        return [], 0

    def has_comments(self, video_id: str) -> bool:
        for handle in self._channel_map.values():
            if self._head(self._key("channels", handle, "comments", f"{video_id}.json")):
                return True
        return False

    # --- Summaries ---

    def save_summary(self, video_id: str, title: str, analysis: dict) -> None:
        handle = self._find_handle_for_video(video_id)
        if not handle:
            return
        self._put_json(
            self._key("channels", handle, "summaries", f"{video_id}.json"),
            {"videoId": video_id, "title": title, "analysis": analysis},
        )

    def get_summary(self, video_id: str) -> dict | None:
        for handle in self._channel_map.values():
            data = self._get_json(self._key("channels", handle, "summaries", f"{video_id}.json"))
            if data and "analysis" in data:
                return data
        return None

    def has_summary(self, video_id: str) -> bool:
        for handle in self._channel_map.values():
            if self._head(self._key("channels", handle, "summaries", f"{video_id}.json")):
                return True
        return False

    # --- Reports ---

    def save_report(self, channel_id: str, report_type: str, content_md: str, tenant_id: str | None = None) -> Any:
        handle = self._resolve_handle(channel_id)
        key = self._key("channels", handle, "reports", f"{report_type}.md")
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content_md.encode("utf-8"), ContentType="text/markdown")
        return key

    def get_report(self, channel_id: str, report_type: str, tenant_id: str | None = None) -> dict | None:
        handle = self._resolve_handle(channel_id)
        key = self._key("channels", handle, "reports", f"{report_type}.md")
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
            content_md = resp["Body"].read().decode("utf-8")
            return {
                "channel_id": channel_id,
                "report_type": report_type,
                "content_md": content_md,
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def list_reports(self, channel_id: str, tenant_id: str | None = None) -> list[dict]:
        handle = self._resolve_handle(channel_id)
        prefix = self._key("channels", handle, "reports") + "/"
        reports = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".md"):
                    report_type = key.rsplit("/", 1)[-1].removesuffix(".md")
                    report = self.get_report(channel_id, report_type, tenant_id)
                    if report:
                        reports.append(report)
        return reports

    # --- Jobs (in-memory, ephemeral) ---

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

    # --- Helpers ---

    def _find_handle_for_video(self, video_id: str) -> str | None:
        for handle in self._channel_map.values():
            videos = self._get_json(self._key("channels", handle, "videos.json"))
            if videos and any(v.get("videoId") == video_id for v in videos):
                return handle
        # No matching channel found — return None to prevent data corruption
        return None
