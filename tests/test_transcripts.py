"""Tests for transcript parsing utilities."""

from tube_agent.services.transcripts import (
    TranscriptExtractor,
    TranscriptUnavailableError,
    _merge_segments,
    _parse_json3,
    _parse_vtt,
)
import pytest


def test_parse_json3_segments():
    body = """
    {
      "events": [
        {"tStartMs": 12000, "dDurationMs": 3000, "segs": [{"utf8": "pricing "}, {"utf8": "strategy"}]},
        {"tStartMs": 16000, "dDurationMs": 2000, "segs": [{"utf8": "\\n"}]}
      ]
    }
    """

    segments = _parse_json3(body)

    assert segments == [
        {"start_seconds": 12.0, "end_seconds": 15.0, "text": "pricing strategy"},
    ]


def test_parse_vtt_segments():
    body = """WEBVTT

00:00:12.000 --> 00:00:15.000
pricing <c>strategy</c>

00:00:16.000 --> 00:00:18.000
customer interviews
"""

    segments = _parse_vtt(body)

    assert segments[0]["start_seconds"] == 12.0
    assert segments[0]["text"] == "pricing strategy"
    assert segments[1]["text"] == "customer interviews"


def test_select_track_prefers_native_auto_over_translated():
    """For an English video with auto-translated KO, ``ko,en`` priority
    should still pick the English source ASR — not the translated track,
    whose URL hits a separately rate-limited endpoint."""
    info = {
        "subtitles": {},
        "automatic_captions": {
            # auto-translated to ko (kind=asr&lang=en&tlang=ko) — what we
            # want to AVOID picking when source captions are available.
            "ko": [
                {"url": "https://www.youtube.com/api/timedtext?lang=en&kind=asr&tlang=ko&fmt=json3", "ext": "json3"}
            ],
            # native English ASR — what we want.
            "en": [
                {"url": "https://www.youtube.com/api/timedtext?lang=en&kind=asr&fmt=json3", "ext": "json3"}
            ],
        },
    }
    extractor = TranscriptExtractor(["ko", "en"])
    track = extractor._select_track(info)
    assert track["language"] == "en"
    assert track["source"] == "auto"
    assert "tlang=" not in track["url"]


def test_select_track_uses_translation_only_as_last_resort():
    """If no native source captions exist, falling back to the translation
    endpoint is acceptable."""
    info = {
        "subtitles": {},
        "automatic_captions": {
            "ko": [
                {"url": "https://www.youtube.com/api/timedtext?lang=en&kind=asr&tlang=ko", "ext": "json3"}
            ],
        },
    }
    extractor = TranscriptExtractor(["ko"])
    track = extractor._select_track(info)
    assert track["language"] == "ko"
    assert track["source"] == "auto-translated"


def test_select_track_prefers_manual_over_auto():
    info = {
        "subtitles": {
            "en": [{"url": "https://example.com/manual.vtt", "ext": "vtt"}],
        },
        "automatic_captions": {
            "en": [{"url": "https://www.youtube.com/api/timedtext?lang=en&kind=asr", "ext": "json3"}],
        },
    }
    extractor = TranscriptExtractor(["en"])
    track = extractor._select_track(info)
    assert track["source"] == "manual"


def test_select_track_raises_when_no_languages_match():
    info = {"subtitles": {}, "automatic_captions": {"ja": [{"url": "x", "ext": "vtt"}]}}
    extractor = TranscriptExtractor(["ko", "en"])
    with pytest.raises(TranscriptUnavailableError):
        extractor._select_track(info)


def test_merge_segments_keeps_timestamp_start():
    segments = [
        {"start_seconds": 12.0, "end_seconds": 14.0, "text": "pricing"},
        {"start_seconds": 15.0, "end_seconds": 18.0, "text": "strategy"},
    ]

    merged = _merge_segments(segments)

    assert merged == [
        {"start_seconds": 12.0, "end_seconds": 18.0, "text": "pricing strategy"},
    ]
