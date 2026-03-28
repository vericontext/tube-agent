"""YouTube Data API v3 client using httpx."""

import os
import httpx
from dotenv import load_dotenv
from scripts.utils import QuotaTracker

load_dotenv()

API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["YOUTUBE_API_KEY"]
        self.http = httpx.Client(timeout=30)
        self.quota = QuotaTracker()

    def _get(self, endpoint: str, params: dict, cost: int = 1) -> dict:
        params["key"] = self.api_key
        resp = self.http.get(f"{API_BASE}/{endpoint}", params=params)
        resp.raise_for_status()
        self.quota.add(endpoint, cost)
        return resp.json()

    def get_channel_by_handle(self, handle: str) -> dict:
        """Fetch channel info by @handle."""
        handle = handle.lstrip("@")
        data = self._get("channels", {
            "forHandle": handle,
            "part": "snippet,contentDetails,statistics,brandingSettings",
        })
        items = data.get("items", [])
        if not items:
            raise ValueError(f"Channel not found: @{handle}")
        return items[0]

    def get_uploads_playlist_items(
        self, playlist_id: str, max_results: int = 100
    ) -> list[dict]:
        """Fetch video IDs from uploads playlist with pagination."""
        items = []
        page_token = None
        while len(items) < max_results:
            page_size = min(50, max_results - len(items))
            params = {
                "playlistId": playlist_id,
                "part": "snippet",
                "maxResults": page_size,
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._get("playlistItems", params)
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return items[:max_results]

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """Fetch video details in batches of 50."""
        all_items = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            data = self._get("videos", {
                "id": ",".join(batch),
                "part": "snippet,contentDetails,statistics",
            })
            all_items.extend(data.get("items", []))
        return all_items

    def get_comment_threads(
        self, video_id: str, max_results: int = 100
    ) -> list[dict]:
        """Fetch top-level comments for a video."""
        try:
            data = self._get("commentThreads", {
                "videoId": video_id,
                "part": "snippet",
                "maxResults": min(max_results, 100),
                "order": "relevance",
                "textFormat": "plainText",
            })
            return data.get("items", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # Comments disabled
                return []
            raise

    def close(self):
        self.http.close()
