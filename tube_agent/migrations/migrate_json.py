"""Migrate existing JSON file data to PostgreSQL.

Usage:
    python -m tube_agent.migrations.migrate_json [--handle HANDLE] [--all]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from tube_agent.config import get_settings
from tube_agent.storage.postgres import PostgresStorage


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def migrate_channel(handle: str, storage: PostgresStorage) -> dict | None:
    """Migrate a single channel's data from JSON files to PostgreSQL."""
    data_dir = BASE_DIR / "data" / handle
    if not data_dir.exists():
        print(f"  No data found for @{handle}")
        return None

    # 1. Channel
    channel_summary = load_json(data_dir / "processed" / "channel_summary.json")
    raw_channel = load_json(data_dir / "raw" / "channel.json")

    if not channel_summary:
        print(f"  No channel_summary.json for @{handle}")
        return None

    channel_id = channel_summary.get("id", "")
    print(f"  Migrating channel: {channel_summary.get('title', handle)}")

    channel_data = {
        "id": channel_id,
        "handle": handle,
        "title": channel_summary.get("title", ""),
        "description": channel_summary.get("description", ""),
        "country": channel_summary.get("country", ""),
        "subscriber_count": channel_summary.get("subscriberCount", 0),
        "view_count": channel_summary.get("viewCount", 0),
        "video_count": channel_summary.get("videoCount", 0),
        "published_at": channel_summary.get("publishedAt"),
        "raw_json": raw_channel or {},
    }
    storage.save_channel(channel_data)

    # 2. Videos
    videos = load_json(data_dir / "processed" / "videos_enriched.json") or []
    if videos:
        storage.save_videos(channel_id, videos)
        print(f"  Migrated {len(videos)} videos")

    # 3. Comments
    comments_dir = data_dir / "raw" / "comments"
    comment_count = 0
    if comments_dir.exists():
        for comment_file in comments_dir.glob("*.json"):
            data = load_json(comment_file)
            if data and "comments" in data:
                video_id = data.get("videoId", comment_file.stem)
                if not storage.has_comments(video_id):
                    storage.save_comments(video_id, data["comments"])
                    comment_count += len(data["comments"])
        print(f"  Migrated {comment_count} comments")

    # 4. Summaries
    summaries_dir = data_dir / "raw" / "summaries"
    summary_count = 0
    if summaries_dir.exists():
        for summary_file in summaries_dir.glob("*.json"):
            data = load_json(summary_file)
            if data and "analysis" in data:
                video_id = data.get("videoId", summary_file.stem)
                if not storage.has_summary(video_id):
                    storage.save_summary(
                        video_id,
                        data.get("title", ""),
                        data["analysis"],
                    )
                    summary_count += 1
        print(f"  Migrated {summary_count} summaries")

    # 5. Reports
    output_dir = BASE_DIR / "output" / handle
    report_count = 0
    if output_dir.exists():
        for md_file in output_dir.glob("*.md"):
            report_type = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            storage.save_report(channel_id, report_type, content)
            report_count += 1
        reports_dir = output_dir / "reports"
        if reports_dir.exists():
            for md_file in reports_dir.glob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                storage.save_report(channel_id, "full_report", content)
                report_count += 1
        print(f"  Migrated {report_count} reports")

    return channel_data


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data to PostgreSQL")
    parser.add_argument("--handle", help="Specific channel handle to migrate")
    parser.add_argument("--all", action="store_true", help="Migrate all channels")
    args = parser.parse_args()

    if not args.handle and not args.all:
        parser.print_help()
        sys.exit(1)

    settings = get_settings()
    storage = PostgresStorage(settings.database_url)
    storage.create_tables()

    if args.all:
        data_dir = BASE_DIR / "data"
        if not data_dir.exists():
            print("No data directory found")
            sys.exit(1)
        handles = [d.name for d in data_dir.iterdir() if d.is_dir()]
        print(f"Migrating {len(handles)} channels...")
        for handle in sorted(handles):
            migrate_channel(handle, storage)
    else:
        handle = args.handle.lstrip("@")
        migrate_channel(handle, storage)

    print("\nMigration complete!")


if __name__ == "__main__":
    main()
