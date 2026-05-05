"""Shared test fixtures."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool

from tube_agent.storage.postgres import PostgresStorage
from tube_agent.api.deps import get_storage
import tube_agent.api.deps as deps_module


@pytest.fixture()
def storage():
    """In-memory SQLite storage for tests (shared connection via StaticPool)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    s = PostgresStorage.__new__(PostgresStorage)
    s.engine = engine
    from sqlalchemy.orm import sessionmaker
    s.SessionLocal = sessionmaker(bind=engine)
    s.create_tables()
    return s


def _make_client(storage_instance):
    """Create TestClient, injecting test storage globally."""
    # Patch the module-level singleton so both lifespan and deps return test storage
    original = deps_module._storage
    deps_module._storage = storage_instance
    try:
        from tube_agent.api.main import create_app
        app = create_app()
        app.dependency_overrides[get_storage] = lambda: storage_instance
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    finally:
        deps_module._storage = original


@pytest.fixture()
def client(storage):
    """FastAPI TestClient with storage override."""
    yield from _make_client(storage)


# --- Sample data ---

SAMPLE_CHANNEL = {
    "id": "UC_test123",
    "handle": "testchannel",
    "title": "Test Channel",
    "description": "A test channel",
    "country": "KR",
    "subscriber_count": 100000,
    "view_count": 5000000,
    "video_count": 200,
    "published_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
    "raw_json": {},
}

SAMPLE_VIDEOS = [
    {
        "videoId": f"vid_{i}",
        "title": f"Test Video {i}",
        "description": f"Description for video {i}",
        "publishedAt": f"2024-{i:02d}-15T00:00:00+00:00" if i <= 12 else "2024-01-01T00:00:00+00:00",
        "tags": ["test", "python"],
        "categoryId": "22",
        "durationSeconds": 600 + i * 100,
        "viewCount": 10000 - i * 500,
        "likeCount": 500 - i * 20,
        "commentCount": 50 - i * 2,
        "likeRatio": 0.05,
        "commentRatio": 0.005,
    }
    for i in range(1, 6)
]

SAMPLE_ANALYSIS = {
    "summary_intro": "This video covers testing in Python.",
    "topics": ["testing", "python", "pytest"],
    "content_type": "tutorial",
    "target_audience": "developers",
    "tone": "educational",
    "mentions": ["pytest", "unittest"],
    "notable_quotes": ["Testing is important."],
    "sections": [
        {"timestamp": "00:00", "title": "Intro", "content": "Introduction to testing"},
    ],
    "summary_bullets": [
        {"title": "Setup", "timestamp": "01:00", "description": "How to set up pytest"},
    ],
}

SAMPLE_TRANSCRIPT = [
    {
        "start_seconds": 12.0,
        "end_seconds": 28.0,
        "text": "The founder explains how pricing strategy changed after customer interviews.",
    },
    {
        "start_seconds": 45.0,
        "end_seconds": 63.0,
        "text": "They compare freemium and enterprise sales for early startup teams.",
    },
]


@pytest.fixture()
def seeded_storage(storage):
    """Storage pre-loaded with sample channel, videos, and summary."""
    storage.save_channel(SAMPLE_CHANNEL)
    storage.save_videos(SAMPLE_CHANNEL["id"], SAMPLE_VIDEOS)
    storage.save_summary("vid_1", "Test Video 1", SAMPLE_ANALYSIS)
    storage.save_transcript_segments("vid_1", "en", "manual", SAMPLE_TRANSCRIPT)
    return storage


@pytest.fixture()
def seeded_client(seeded_storage):
    """TestClient with pre-loaded data."""
    yield from _make_client(seeded_storage)
