"""Tests for the embedding provider abstraction and storage round-trip."""

import numpy as np
import pytest


class _FakeProvider:
    """Deterministic in-memory provider used to avoid downloading real models in tests."""

    def __init__(self, dim: int = 4):
        self._dim = dim
        # Map known phrases to fixed unit vectors so we can assert ordering.
        self._table = {
            "fundraising": np.array([1, 0, 0, 0], dtype=np.float32),
            "pricing strategy": np.array([0.95, 0.31, 0, 0], dtype=np.float32),
            "freemium and enterprise sales": np.array([0.5, 0.86, 0, 0], dtype=np.float32),
            "kubernetes networking": np.array([0, 0, 1, 0], dtype=np.float32),
        }

    def embed(self, texts):
        out = []
        for t in texts:
            t = t.lower()
            v = self._table.get(t)
            if v is None:
                # Hash to a stable orthogonal-ish vector for unknown text
                rng = np.random.default_rng(abs(hash(t)) % (2**32))
                v = rng.standard_normal(self._dim).astype(np.float32)
            v = v / (np.linalg.norm(v) or 1.0)
            out.append(v.astype(np.float32))
        return np.asarray(out, dtype=np.float32)

    @property
    def name(self) -> str:
        return "fake:test"

    @property
    def dimension(self) -> int:
        return self._dim


def _seed_segments(storage):
    """Insert one channel + one video + a few transcript segments. Returns segment ids."""
    storage.save_channel({
        "id": "UC_test",
        "handle": "embedchannel",
        "title": "Embed Channel",
        "description": "",
        "country": "KR",
        "subscriber_count": 0,
        "view_count": 0,
        "video_count": 1,
        "raw_json": {},
    })
    storage.save_videos("UC_test", [{
        "videoId": "vid_emb",
        "title": "Pricing strategy and fundraising",
        "description": "",
        "publishedAt": "2024-01-01T00:00:00+00:00",
        "tags": [],
        "categoryId": "22",
        "durationSeconds": 600,
        "viewCount": 1, "likeCount": 0, "commentCount": 0,
        "likeRatio": 0.0, "commentRatio": 0.0,
    }])
    saved = storage.save_transcript_segments(
        "vid_emb", "en", "manual",
        [
            {"start_seconds": 0.0, "end_seconds": 5.0, "text": "pricing strategy"},
            {"start_seconds": 5.0, "end_seconds": 10.0, "text": "freemium and enterprise sales"},
            {"start_seconds": 10.0, "end_seconds": 15.0, "text": "kubernetes networking"},
        ],
    )
    assert saved == 3

    # Hydrate ids so the test can assert the right ordering
    rows = storage.get_transcript("vid_emb")
    return rows


def test_list_unembedded_segments_returns_all_initially(storage):
    _seed_segments(storage)
    pending = storage.list_unembedded_segments("fake:test")
    assert len(pending) == 3


def test_save_and_search_roundtrip(storage):
    _seed_segments(storage)
    provider = _FakeProvider()

    pending = storage.list_unembedded_segments(provider.name)
    texts = [p["text"] for p in pending]
    vectors = provider.embed(texts)
    storage.save_embeddings(
        list(zip([p["id"] for p in pending], [v.tolist() for v in vectors])),
        provider.name,
        provider.dimension,
    )

    # Now nothing is pending
    assert storage.list_unembedded_segments(provider.name) == []

    # Querying with "fundraising" should rank pricing/freemium higher than kubernetes
    q = provider.embed(["fundraising"])[0].tolist()
    hits = storage.search_semantic(q, provider.name, limit=3)
    assert len(hits) == 3
    assert hits[0]["text"] == "pricing strategy"
    assert hits[-1]["text"] == "kubernetes networking"
    # Cosine of normalised vectors stays in [-1, 1]
    assert -1.0 <= hits[0]["score"] <= 1.0001
    assert hits[0]["score"] > hits[-1]["score"]


def test_search_semantic_respects_channel_filter(storage):
    _seed_segments(storage)
    provider = _FakeProvider()
    pending = storage.list_unembedded_segments(provider.name)
    vectors = provider.embed([p["text"] for p in pending])
    storage.save_embeddings(
        list(zip([p["id"] for p in pending], [v.tolist() for v in vectors])),
        provider.name,
        provider.dimension,
    )

    q = provider.embed(["fundraising"])[0].tolist()
    same_channel = storage.search_semantic(q, provider.name, channel_id="UC_test")
    assert len(same_channel) == 3

    other_channel = storage.search_semantic(q, provider.name, channel_id="UC_other")
    assert other_channel == []


def test_save_embeddings_is_idempotent(storage):
    _seed_segments(storage)
    provider = _FakeProvider()
    pending = storage.list_unembedded_segments(provider.name)
    vectors = provider.embed([p["text"] for p in pending])
    items = list(zip([p["id"] for p in pending], [v.tolist() for v in vectors]))

    storage.save_embeddings(items, provider.name, provider.dimension)
    storage.save_embeddings(items, provider.name, provider.dimension)  # re-save same

    q = provider.embed(["fundraising"])[0].tolist()
    hits = storage.search_semantic(q, provider.name, limit=10)
    # Still exactly 3 segments — no duplicate rows
    assert len(hits) == 3


def test_pipeline_embed_step_is_skippable(storage):
    """embed_transcripts should be a no-op when nothing is pending."""
    from tube_agent.services.pipeline import embed_transcripts

    provider = _FakeProvider()
    n = embed_transcripts(storage, provider)
    assert n == 0  # no segments yet
