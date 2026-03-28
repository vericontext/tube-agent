"""Fetch recent videos from a channel's uploads playlist."""

from scripts.youtube_client import YouTubeClient
from scripts.utils import (
    save_json,
    parse_duration,
    format_number,
)


def fetch_videos(
    client: YouTubeClient, uploads_playlist_id: str, max_videos: int = 100,
    paths: dict = None,
) -> list[dict]:
    """Fetch video metadata and save enriched data."""
    print(f"Fetching up to {max_videos} videos...")
    playlist_items = client.get_uploads_playlist_items(
        uploads_playlist_id, max_videos
    )
    video_ids = [
        item["snippet"]["resourceId"]["videoId"] for item in playlist_items
    ]
    print(f"  Found {len(video_ids)} videos, fetching details...")
    details = client.get_video_details(video_ids)
    save_json(details, paths["raw"] / "videos.json")

    enriched = []
    for v in details:
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})
        content = v.get("contentDetails", {})
        duration_sec = parse_duration(content.get("duration", ""))
        view_count = int(stats.get("viewCount", 0))
        like_count = int(stats.get("likeCount", 0))
        comment_count = int(stats.get("commentCount", 0))

        enriched.append({
            "videoId": v["id"],
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "publishedAt": snippet.get("publishedAt", ""),
            "tags": snippet.get("tags", []),
            "categoryId": snippet.get("categoryId", ""),
            "duration": content.get("duration", ""),
            "durationSeconds": duration_sec,
            "viewCount": view_count,
            "viewCountFormatted": format_number(view_count),
            "likeCount": like_count,
            "commentCount": comment_count,
            "likeRatio": round(like_count / view_count, 6) if view_count else 0,
            "commentRatio": round(comment_count / view_count, 6) if view_count else 0,
        })

    save_json(enriched, paths["processed"] / "videos_enriched.json")
    print(f"  Saved {len(enriched)} enriched videos")
    return enriched
