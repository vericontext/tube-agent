"""CLI orchestrator for fetching all YouTube channel data."""

import argparse

from tube_agent.services.pipeline import run_full_pipeline
from tube_agent.storage.local import LocalStorage
from tube_agent.storage.postgres import PostgresStorage
from tube_agent.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube channel data")
    parser.add_argument("handle", help="YouTube channel handle (e.g. @eo_korea)")
    parser.add_argument("--max-videos", type=int, default=100)
    parser.add_argument("--with-comments", action="store_true",
                        help="Fetch comments (off by default for transcript-search indexing)")
    parser.add_argument("--with-summaries", action="store_true",
                        help="Run Gemini summaries (off by default for transcript-search indexing)")
    parser.add_argument("--skip-comments", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--skip-summaries", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--skip-transcripts", action="store_true",
                        help="Skip transcript indexing")
    parser.add_argument("--transcript-languages", default="ko,en",
                        help="Comma-separated transcript language priority (default: ko,en)")
    parser.add_argument("--skip-report", action="store_true",
                        help="Skip automatic report generation")
    parser.add_argument("--summary-max", type=int, default=None,
                        help="Max videos to analyze with Gemini (default: all)")
    parser.add_argument("--media-resolution", choices=["low", "medium", "high"],
                        default="low", help="Gemini media resolution (default: low)")
    parser.add_argument("--workers", type=int, default=5,
                        help="Concurrent Gemini workers (default: 5)")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Skip transcript embedding generation")
    args = parser.parse_args()

    handle = args.handle.lstrip("@")
    settings = get_settings()

    if settings.database_url.startswith(("postgresql", "sqlite")):
        storage = PostgresStorage(settings.database_url)
        storage.create_tables()
    else:
        storage = LocalStorage()

    embedder = None
    fetch_transcript_data = not args.skip_transcripts
    if fetch_transcript_data and not args.skip_embeddings:
        from tube_agent.services.embeddings import get_default_provider
        try:
            embedder = get_default_provider()
        except Exception as e:
            print(f"warning: embedder unavailable, transcripts will not be embedded: {e}")

    run_full_pipeline(
        handle=handle,
        storage=storage,
        youtube_api_key=settings.youtube_api_key,
        gemini_api_key=settings.gemini_api_key,
        max_videos=args.max_videos,
        skip_comments=(not args.with_comments) or args.skip_comments,
        skip_summaries=(not args.with_summaries) or args.skip_summaries,
        fetch_transcript_data=fetch_transcript_data,
        transcript_languages=[lang.strip() for lang in args.transcript_languages.split(",") if lang.strip()],
        summary_max=args.summary_max,
        media_resolution=args.media_resolution,
        skip_report=args.skip_report,
        max_workers=args.workers,
        skip_embeddings=args.skip_embeddings,
        embedder=embedder,
    )


if __name__ == "__main__":
    main()
