"""Fetch channel metadata."""

from pathlib import Path

from scripts.youtube_client import YouTubeClient
from scripts.utils import save_json, format_number


def fetch_channel(client: YouTubeClient, handle: str, paths: dict) -> dict:
    """Fetch and save channel info. Returns channel data."""
    print(f"Fetching channel: @{handle}")
    channel = client.get_channel_by_handle(handle)
    save_json(channel, paths["raw"] / "channel.json")

    stats = channel.get("statistics", {})
    snippet = channel.get("snippet", {})
    summary = {
        "id": channel["id"],
        "title": snippet.get("title", ""),
        "handle": handle,
        "description": snippet.get("description", ""),
        "publishedAt": snippet.get("publishedAt", ""),
        "country": snippet.get("country", ""),
        "subscriberCount": int(stats.get("subscriberCount", 0)),
        "subscriberCountFormatted": format_number(stats.get("subscriberCount", 0)),
        "viewCount": int(stats.get("viewCount", 0)),
        "viewCountFormatted": format_number(stats.get("viewCount", 0)),
        "videoCount": int(stats.get("videoCount", 0)),
        "uploadsPlaylistId": (
            channel.get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads", "")
        ),
    }
    save_json(summary, paths["processed"] / "channel_summary.json")
    print(f"  Channel: {summary['title']} ({summary['subscriberCountFormatted']} subscribers)")
    return summary
