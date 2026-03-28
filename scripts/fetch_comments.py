"""Fetch comments for videos."""

from scripts.youtube_client import YouTubeClient
from scripts.utils import save_json


def fetch_comments(
    client: YouTubeClient, videos: list[dict], paths: dict,
    max_per_video: int = 100,
) -> None:
    """Fetch top comments for each video."""
    print(f"Fetching comments for {len(videos)} videos...")
    all_summaries = []
    success_count = 0
    skipped_count = 0

    for i, v in enumerate(videos, 1):
        vid = v["videoId"]
        out_path = paths["raw"] / "comments" / f"{vid}.json"
        if out_path.exists():
            skipped_count += 1
            continue

        threads = client.get_comment_threads(vid, max_per_video)

        if threads:
            comments = []
            for t in threads:
                snippet = t["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": snippet.get("authorDisplayName", ""),
                    "text": snippet.get("textDisplay", ""),
                    "likeCount": snippet.get("likeCount", 0),
                    "publishedAt": snippet.get("publishedAt", ""),
                })

            save_json(
                {"videoId": vid, "comments": comments},
                out_path,
            )
            all_summaries.append({
                "videoId": vid,
                "title": v.get("title", ""),
                "commentCount": len(comments),
                "topComment": comments[0]["text"] if comments else "",
            })
            success_count += 1

        if i % 20 == 0:
            print(f"  Progress: {i}/{len(videos)} ({success_count} with comments)")

    save_json(all_summaries, paths["processed"] / "comments_summary.json")
    print(f"  Comments: {success_count} new, {skipped_count} skipped")
