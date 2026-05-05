"""Pipeline orchestration - shared logic for CLI and API background tasks."""

import hashlib
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from tube_agent.storage.base import StorageBackend
from tube_agent.services.youtube import YouTubeClient
from tube_agent.services.gemini import GeminiClient

logger = logging.getLogger(__name__)


def _anonymize(name: str) -> str:
    """Hash author name for privacy."""
    return f"user_{hashlib.sha256(name.encode()).hexdigest()[:8]}"


def parse_duration(iso_duration: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or "")
    if not match:
        return 0
    h, m, s = (int(v or 0) for v in match.groups())
    return h * 3600 + m * 60 + s


def format_number(n: int | float) -> str:
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def fetch_channel(
    yt_client: YouTubeClient,
    handle: str,
    storage: StorageBackend,
) -> dict:
    """Fetch channel metadata and save via storage backend."""
    logger.info("Fetching channel: @%s", handle)
    raw = yt_client.get_channel_by_handle(handle)
    stats = raw.get("statistics", {})
    snippet = raw.get("snippet", {})

    channel_data = {
        "id": raw["id"],
        "handle": handle,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "country": snippet.get("country", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "view_count": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "published_at": snippet.get("publishedAt"),
        "raw_json": raw,
        "uploadsPlaylistId": (
            raw.get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads", "")
        ),
    }

    storage.save_channel(channel_data)
    logger.info("  Channel: %s (%s subscribers)", channel_data['title'], format_number(channel_data['subscriber_count']))
    return channel_data


def fetch_videos(
    yt_client: YouTubeClient,
    channel_data: dict,
    max_videos: int,
    storage: StorageBackend,
) -> list[dict]:
    """Fetch videos and save via storage backend."""
    playlist_id = channel_data["uploadsPlaylistId"]
    logger.info("Fetching up to %d videos...", max_videos)

    playlist_items = yt_client.get_uploads_playlist_items(playlist_id, max_videos)
    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in playlist_items]
    logger.info("  Found %d videos, fetching details...", len(video_ids))

    details = yt_client.get_video_details(video_ids)

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

    storage.save_videos(channel_data["id"], enriched)
    logger.info("  Saved %d enriched videos", len(enriched))
    return enriched


def fetch_comments(
    yt_client: YouTubeClient,
    videos: list[dict],
    storage: StorageBackend,
    max_per_video: int = 100,
) -> None:
    """Fetch comments for each video."""
    logger.info("Fetching comments for %d videos...", len(videos))
    success_count = 0
    skipped_count = 0

    for i, v in enumerate(videos, 1):
        vid = v["videoId"]
        if storage.has_comments(vid):
            skipped_count += 1
            continue

        threads = yt_client.get_comment_threads(vid, max_per_video)
        if threads:
            comments = []
            for t in threads:
                snippet = t["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": _anonymize(snippet.get("authorDisplayName", "")),
                    "text": snippet.get("textDisplay", ""),
                    "likeCount": snippet.get("likeCount", 0),
                    "publishedAt": snippet.get("publishedAt", ""),
                })
            storage.save_comments(vid, comments)
            success_count += 1

        if i % 20 == 0:
            logger.info("  Progress: %d/%d (%d with comments)", i, len(videos), success_count)

    logger.info("  Comments: %d new, %d skipped", success_count, skipped_count)


def fetch_transcripts(
    videos: list[dict],
    storage: StorageBackend,
    languages: list[str] | None = None,
    max_workers: int = 5,
) -> dict[str, bool]:
    """Fetch caption-backed transcript segments for each video."""
    from tube_agent.services.transcripts import TranscriptExtractor, TranscriptUnavailableError

    target_languages = languages or ["ko", "en"]
    extractor = TranscriptExtractor(target_languages)
    logger.info(
        "Fetching transcripts for %d videos (languages=%s, workers=%d)...",
        len(videos),
        ",".join(target_languages),
        max_workers,
    )

    results: dict[str, bool] = {}
    success_count = 0
    skipped_count = 0
    unavailable_count = 0

    to_process: list[dict] = []
    for video in videos:
        vid = video["videoId"]
        if any(storage.has_transcript(vid, language) for language in target_languages):
            results[vid] = True
            skipped_count += 1
        else:
            to_process.append(video)

    if skipped_count:
        logger.info(
            "  Skipped %d already-indexed videos, processing %d remaining",
            skipped_count,
            len(to_process),
        )

    def _process_one(video: dict) -> tuple[str, bool, str | None]:
        vid = video["videoId"]
        try:
            transcript = extractor.extract(vid)
            saved = storage.save_transcript_segments(
                transcript.video_id,
                transcript.language,
                transcript.source,
                transcript.segments,
            )
            return vid, saved > 0, None
        except TranscriptUnavailableError as e:
            return vid, False, f"unavailable: {e}"
        except Exception as e:
            return vid, False, f"error: {e}"

    completed = 0
    total = len(to_process)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_one, v): v for v in to_process}
        for future in as_completed(futures):
            vid, ok, note = future.result()
            results[vid] = ok
            if ok:
                success_count += 1
            else:
                unavailable_count += 1
                if note and note.startswith("error"):
                    logger.warning("  Transcript %s: %s", vid, note)
                elif note:
                    logger.info("  Transcript %s: %s", vid, note)
            completed += 1
            if completed % 10 == 0 or completed == total:
                logger.info(
                    "  Transcript progress: %d/%d (%d OK, %d skipped, %d unavailable)",
                    completed,
                    total,
                    success_count,
                    skipped_count,
                    unavailable_count,
                )

    logger.info("  Transcripts: %d new, %d skipped, %d unavailable", success_count, skipped_count, unavailable_count)
    return results


def embed_transcripts(
    storage: StorageBackend,
    embedder,
    channel_id: str | None = None,
    batch_size: int = 64,
) -> int:
    """Generate embeddings for any transcript segments missing one for this model.

    Skips segments already embedded for the same model. Embeddings are
    L2-normalised and persisted as float32 BLOBs alongside the model identifier.
    """
    pending = storage.list_unembedded_segments(embedder.name, channel_id=channel_id)
    if not pending:
        logger.info("Embeddings up to date for model %s", embedder.name)
        return 0

    logger.info(
        "Embedding %d transcript segments with %s (dim=%d)...",
        len(pending),
        embedder.name,
        embedder.dimension,
    )

    embedded = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        texts = [seg["text"] for seg in batch]
        vectors = embedder.embed(texts)
        items = [
            (seg["id"], vectors[i].astype("float32").tolist())
            for i, seg in enumerate(batch)
        ]
        storage.save_embeddings(items, embedder.name, embedder.dimension)
        embedded += len(batch)
        if (start + batch_size) % (batch_size * 8) == 0 or embedded == len(pending):
            logger.info("  Embedding progress: %d/%d", embedded, len(pending))
    logger.info("  Embeddings: %d new", embedded)
    return embedded


def fetch_summaries(
    videos: list[dict],
    storage: StorageBackend,
    gemini_client: GeminiClient,
    max_videos: int | None = None,
    media_resolution: str = "low",
    max_workers: int = 5,
) -> dict[str, bool]:
    """Analyze videos with Gemini and save via storage backend."""
    target = videos[:max_videos] if max_videos else videos
    logger.info("Analyzing %d videos with Gemini (resolution=%s, workers=%d)...", len(target), media_resolution, max_workers)

    results = {}
    success_count = 0
    skipped_count = 0

    # Pre-check which videos already have summaries
    to_process = []
    for video in target:
        vid = video["videoId"]
        if storage.has_summary(vid):
            results[vid] = True
            skipped_count += 1
        else:
            to_process.append(video)

    if skipped_count:
        logger.info("  Skipped %d already-summarized videos, processing %d remaining", skipped_count, len(to_process))

    def _process_one(video: dict) -> tuple[str, bool]:
        vid = video["videoId"]
        for attempt in range(2):
            try:
                raw_text = gemini_client.analyze_video(vid, media_resolution=media_resolution)
                cleaned = raw_text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                try:
                    analysis = json.loads(cleaned)
                except json.JSONDecodeError:
                    fixed = re.sub(r'[\x00-\x1f]', lambda m: f'\\u{ord(m.group()):04x}', cleaned)
                    analysis = json.loads(fixed)

                storage.save_summary(vid, video.get("title", ""), analysis)
                return vid, True
            except json.JSONDecodeError as e:
                if attempt == 0:
                    logger.warning("  JSON parse failed for %s, retrying... (%s)", vid, e)
                    time.sleep(2)
                    continue
                logger.error("  Error analyzing %s: %s", vid, e)
                return vid, False
            except Exception as e:
                logger.error("  Error analyzing %s: %s", vid, e)
                return vid, False
        return vid, False

    completed = 0
    total = len(to_process)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_one, v): v for v in to_process}
        for future in as_completed(futures):
            vid, ok = future.result()
            results[vid] = ok
            if ok:
                success_count += 1
            completed += 1
            if completed % 5 == 0 or completed == total:
                logger.info("  Progress: %d/%d (%d OK, %d skipped)", completed, total, success_count, skipped_count)

    logger.info("  Summaries: %d new, %d skipped", success_count, skipped_count)
    logger.info("  %s", gemini_client.summary())
    return results


def fetch_transcript_summaries(
    videos: list[dict],
    storage: StorageBackend,
    gemini_client: GeminiClient,
    max_videos: int | None = 10,
    language: str = "en",
) -> dict[str, bool]:
    """Generate summaries from stored transcript segments for the latest videos."""
    from tube_agent.services.summaries import (
        SummaryGenerationError,
        generate_and_save_transcript_summary,
    )

    target = sorted(
        videos,
        key=lambda v: v.get("publishedAt", v.get("published_at", "")) or "",
        reverse=True,
    )
    if max_videos is not None:
        target = target[:max_videos]

    logger.info("Generating transcript summaries for %d videos (language=%s)...", len(target), language)
    results = {}
    success_count = 0
    skipped_count = 0

    for video in target:
        vid = video["videoId"]
        if storage.has_summary(vid):
            results[vid] = True
            skipped_count += 1
            continue
        try:
            generate_and_save_transcript_summary(storage, vid, gemini_client, language=language)
            results[vid] = True
            success_count += 1
        except SummaryGenerationError as e:
            logger.info("  Transcript summary skipped for %s: %s", vid, e)
            results[vid] = False
        except Exception as e:
            logger.warning("  Transcript summary failed for %s: %s", vid, e)
            results[vid] = False

    logger.info("  Transcript summaries: %d new, %d skipped", success_count, skipped_count)
    logger.info("  %s", gemini_client.summary())
    return results


def run_full_pipeline(
    handle: str,
    storage: StorageBackend,
    youtube_api_key: str,
    gemini_api_key: str,
    max_videos: int = 100,
    skip_comments: bool = True,
    skip_summaries: bool = True,
    fetch_transcript_data: bool = True,
    transcript_languages: list[str] | None = None,
    summary_max: int | None = None,
    media_resolution: str = "low",
    summary_mode: str = "transcript",
    summary_language: str = "en",
    skip_report: bool = False,
    max_workers: int = 5,
    skip_embeddings: bool = False,
    embedder=None,
) -> dict:
    """Run the full data collection pipeline."""
    # Clean up stale YouTube API data (30-day retention policy)
    # and anonymize any existing non-hashed comment authors
    from tube_agent.services.data_retention import cleanup_stale_data, anonymize_existing_comments
    from tube_agent.storage.postgres import PostgresStorage
    if isinstance(storage, PostgresStorage):
        try:
            result = cleanup_stale_data(storage)
            if any(result.values()):
                logger.info("Data retention cleanup: %s", result)
            anonymize_existing_comments(storage)
        except Exception as e:
            logger.warning("Data retention cleanup failed (non-fatal): %s", e)

    yt_client = YouTubeClient(youtube_api_key)
    gemini = None
    try:
        channel_data = fetch_channel(yt_client, handle, storage)
        videos = fetch_videos(yt_client, channel_data, max_videos, storage)

        transcript_results = {}
        if fetch_transcript_data:
            transcript_results = fetch_transcripts(videos, storage, transcript_languages, max_workers=max_workers)

        embedded_count = 0
        if fetch_transcript_data and not skip_embeddings and embedder is not None:
            try:
                embedded_count = embed_transcripts(
                    storage, embedder, channel_id=channel_data["id"]
                )
            except Exception as e:
                logger.warning("Embedding stage failed (non-fatal): %s", e)

        if not skip_comments:
            fetch_comments(yt_client, videos, storage)

        summary_results = {}
        if not skip_summaries and not gemini_api_key:
            logger.warning("Gemini API key is not set; skipping summaries and report")
        elif not skip_summaries:
            gemini = GeminiClient(gemini_api_key)
            if summary_mode == "transcript":
                summary_results = fetch_transcript_summaries(
                    videos,
                    storage,
                    gemini,
                    max_videos=summary_max if summary_max is not None else 10,
                    language=summary_language,
                )
            else:
                summary_results = fetch_summaries(videos, storage, gemini, summary_max, media_resolution, max_workers=max_workers)

        # Generate report
        report_generated = False
        if not skip_report and not skip_summaries and gemini_api_key:
            from tube_agent.services.report import generate_channel_report
            if gemini is None:
                gemini = GeminiClient(gemini_api_key)
            logger.info("Generating channel overview report...")
            generate_channel_report(channel_data["id"], handle, storage, gemini)
            report_generated = True

        logger.info("Done! %s", yt_client.quota.summary())
        return {
            "channel_id": channel_data["id"],
            "handle": handle,
            "video_count": len(videos),
            "transcript_count": sum(1 for ok in transcript_results.values() if ok),
            "summary_count": sum(1 for ok in summary_results.values() if ok),
            "embedded_count": embedded_count,
            "report_generated": report_generated,
            "quota": yt_client.quota.summary(),
        }
    finally:
        yt_client.close()
