"""YouTube API data retention policy — 30-day expiry for API-sourced data."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, delete

from tube_agent.models.database import Channel, Video, Comment

logger = logging.getLogger(__name__)


def _anonymize(name: str) -> str:
    """Hash author name for privacy."""
    return f"user_{hashlib.sha256(name.encode()).hexdigest()[:8]}"


def cleanup_stale_data(storage, max_age_days: int = 30) -> dict:
    """Delete YouTube API data older than max_age_days.

    - Videos: NULL out YouTube API statistics (view_count, like_count, etc.)
      but keep title, description, and AI-generated summaries.
    - Comments: Delete entirely.
    - Channels: NULL out statistics fields.

    Returns a dict with counts of affected rows.
    """
    from tube_agent.storage.postgres import PostgresStorage

    if not isinstance(storage, PostgresStorage):
        return {"videos_cleared": 0, "comments_deleted": 0, "channels_cleared": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    with storage.get_session() as session:
        # Videos: clear YouTube API statistics for stale records
        video_result = session.execute(
            update(Video)
            .where(Video.fetched_at < cutoff)
            .where(Video.view_count.isnot(None))
            .values(
                view_count=None,
                like_count=None,
                comment_count=None,
                like_ratio=None,
                comment_ratio=None,
            )
        )

        # Comments: delete stale records
        comment_result = session.execute(
            delete(Comment).where(Comment.fetched_at < cutoff)
        )

        # Channels: clear statistics for stale records
        channel_result = session.execute(
            update(Channel)
            .where(Channel.updated_at < cutoff)
            .where(Channel.subscriber_count.isnot(None))
            .values(
                subscriber_count=None,
                view_count=None,
                video_count=None,
            )
        )

        session.commit()

        result = {
            "videos_cleared": video_result.rowcount,
            "comments_deleted": comment_result.rowcount,
            "channels_cleared": channel_result.rowcount,
        }

        if any(result.values()):
            logger.info(
                "Data retention cleanup: %d video stats cleared, "
                "%d comments deleted, %d channel stats cleared",
                result["videos_cleared"],
                result["comments_deleted"],
                result["channels_cleared"],
            )

        return result


def anonymize_existing_comments(storage) -> int:
    """Migrate existing comments: hash any non-anonymized author names.

    Skips authors already in 'user_XXXXXXXX' format.
    Returns the number of updated rows.
    """
    from tube_agent.storage.postgres import PostgresStorage

    if not isinstance(storage, PostgresStorage):
        return 0

    updated = 0
    with storage.get_session() as session:
        # Fetch comments whose author is not already anonymized
        comments = session.execute(
            select(Comment)
            .where(~Comment.author.like("user_%"))
            .where(Comment.author != "")
        ).scalars().all()

        for comment in comments:
            comment.author = _anonymize(comment.author)
            updated += 1

        if updated:
            session.commit()
            logger.info("Anonymized %d existing comment authors", updated)

    return updated


def anonymize_local_comments(base_dir: str | None = None) -> int:
    """Anonymize comment authors in local JSON files (CLI mode).

    Scans data/*/raw/comments/*.json and hashes non-anonymized author names.
    Returns the number of files updated.
    """
    import json
    from pathlib import Path

    root = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent
    data_dir = root / "data"
    if not data_dir.exists():
        return 0

    files_updated = 0
    for comment_file in data_dir.glob("*/raw/comments/*.json"):
        try:
            with open(comment_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        comments = data.get("comments", [])
        changed = False
        for c in comments:
            author = c.get("author", "")
            if author and not author.startswith("user_"):
                c["author"] = _anonymize(author)
                changed = True

        if changed:
            with open(comment_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            files_updated += 1

    if files_updated:
        logger.info("Anonymized authors in %d local comment files", files_updated)

    return files_updated
