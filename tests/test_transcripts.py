"""Tests for transcript parsing utilities."""

from tube_agent.services.transcripts import _merge_segments, _parse_json3, _parse_vtt


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


def test_merge_segments_keeps_timestamp_start():
    segments = [
        {"start_seconds": 12.0, "end_seconds": 14.0, "text": "pricing"},
        {"start_seconds": 15.0, "end_seconds": 18.0, "text": "strategy"},
    ]

    merged = _merge_segments(segments)

    assert merged == [
        {"start_seconds": 12.0, "end_seconds": 18.0, "text": "pricing strategy"},
    ]
