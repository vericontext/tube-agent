"""Tests for transcript-backed summary generation."""

import json

import pytest

from tests.conftest import SAMPLE_VIDEOS, SAMPLE_TRANSCRIPT
from tube_agent.services.summaries import (
    SummaryGenerationError,
    generate_transcript_summary,
)


class FakeGemini:
    def __init__(self, text: str):
        self.text = text
        self.prompts = []

    def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.text


def _summary_json() -> str:
    return json.dumps({
        "summary_intro": "This video explains pricing strategy for early startup teams.",
        "summary_bullets": [
            {
                "title": "Pricing changes after interviews",
                "timestamp": "00:12",
                "description": "The founder explains how customer interviews changed the pricing approach.",
            }
        ],
        "sections": [
            {
                "timestamp": "00:12",
                "title": "Pricing strategy",
                "content": "The segment covers how pricing shifted after customer discovery.",
            }
        ],
        "topics": ["pricing", "startups"],
        "content_type": "interview",
        "target_audience": "startup founders",
        "tone": "educational",
        "mentions": ["freemium"],
        "notable_quotes": ["Pricing should be shaped by customer discovery."],
    })


def test_generate_transcript_summary_returns_normalized_shape():
    fake = FakeGemini(f"```json\n{_summary_json()}\n```")

    summary = generate_transcript_summary(SAMPLE_VIDEOS[0], SAMPLE_TRANSCRIPT, fake)

    assert summary["summary_intro"].startswith("This video explains")
    assert summary["summary_bullets"][0]["timestamp"] == "00:12"
    assert summary["sections"][0]["title"] == "Pricing strategy"
    assert summary["topics"] == ["pricing", "startups"]
    assert "[00:12]" in fake.prompts[0]


def test_generate_transcript_summary_requires_segments():
    with pytest.raises(SummaryGenerationError):
        generate_transcript_summary(SAMPLE_VIDEOS[0], [], FakeGemini(_summary_json()))
