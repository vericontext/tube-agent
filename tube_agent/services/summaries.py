"""Transcript-backed video summary generation."""

from __future__ import annotations

import json
import re

from tube_agent.services.gemini import GeminiClient
from tube_agent.storage.base import StorageBackend


TRANSCRIPT_SUMMARY_PROMPT = """\
You are summarizing a YouTube video from its timestamped transcript.
Write the result in English. Respond ONLY with valid JSON, no markdown fences.

Video title: {title}
Published at: {published_at}

Return this exact shape:
{{
  "summary_intro": "A concise 4-6 sentence overview of what the video is about, who it is for, and why it matters.",
  "summary_bullets": [
    {{
      "title": "Key point title",
      "timestamp": "MM:SS",
      "description": "2-3 sentences explaining the point, with concrete details from the transcript."
    }}
  ],
  "sections": [
    {{
      "timestamp": "MM:SS",
      "title": "Section title",
      "content": "3-5 sentences summarizing this segment in detail."
    }}
  ],
  "topics": ["topic1", "topic2"],
  "content_type": "interview | lecture | vlog | documentary | review | tutorial | entertainment | other",
  "target_audience": "Who would benefit from this video",
  "tone": "serious | humorous | educational | inspirational | casual | formal",
  "mentions": ["People, companies, products, books, or organizations mentioned"],
  "notable_quotes": ["Paraphrased notable statements; do not quote verbatim"]
}}

Rules:
- Base the summary only on the transcript below.
- Include 4-7 summary_bullets.
- Include 5-10 sections following the video's flow.
- Prefer timestamps from the transcript. Use "00:00" only if no better timestamp is available.
- Do not include direct quotes. Paraphrase.
- Keep topics short and searchable.

Timestamped transcript:
{transcript}
"""


class SummaryGenerationError(RuntimeError):
    """Raised when a transcript summary cannot be generated."""


def generate_transcript_summary(
    video: dict,
    segments: list[dict],
    gemini_client: GeminiClient,
    language: str = "en",
) -> dict:
    """Generate a structured summary from timestamped transcript segments."""
    if language != "en":
        raise SummaryGenerationError("Only English transcript summaries are supported in this build")
    if not segments:
        raise SummaryGenerationError("No transcript segments available")

    prompt = TRANSCRIPT_SUMMARY_PROMPT.format(
        title=video.get("title", ""),
        published_at=video.get("published_at", video.get("publishedAt", "")),
        transcript=_format_transcript_for_prompt(segments),
    )
    return _normalize_summary(_parse_json_response(gemini_client.generate_text(prompt)))


def generate_and_save_transcript_summary(
    storage: StorageBackend,
    video_id: str,
    gemini_client: GeminiClient,
    language: str = "en",
) -> dict:
    """Generate a transcript summary for one video, save it, and return it."""
    video = storage.get_video(video_id)
    if not video:
        raise SummaryGenerationError(f"Video not found: {video_id}")
    segments = storage.get_transcript(video_id)
    if not segments:
        raise SummaryGenerationError(f"Transcript not found for video: {video_id}")

    analysis = generate_transcript_summary(video, segments, gemini_client, language=language)
    raw = {
        **analysis,
        "summary_mode": "transcript",
        "summary_language": language,
    }
    storage.save_summary(video_id, video.get("title", ""), raw)
    saved = storage.get_summary(video_id)
    if not saved:
        raise SummaryGenerationError(f"Failed to save summary for video: {video_id}")
    return saved


def _format_transcript_for_prompt(segments: list[dict], max_chars: int = 90_000) -> str:
    lines = []
    used = 0
    for segment in segments:
        timestamp = segment.get("timestamp") or _format_timestamp(segment.get("start_seconds"))
        text = re.sub(r"\s+", " ", segment.get("text", "")).strip()
        if not text:
            continue
        line = f"[{timestamp}] {text}"
        if used + len(line) + 1 > max_chars:
            lines.append("[Transcript truncated for length.]")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        fixed = re.sub(r"[\x00-\x1f]", lambda m: f"\\u{ord(m.group()):04x}", cleaned)
        return json.loads(fixed)


def _normalize_summary(data: dict) -> dict:
    return {
        "summary_intro": data.get("summary_intro") or "",
        "summary_bullets": [
            {
                "title": item.get("title", ""),
                "timestamp": item.get("timestamp", "00:00"),
                "description": item.get("description", ""),
            }
            for item in (data.get("summary_bullets") or [])
            if isinstance(item, dict)
        ],
        "sections": [
            {
                "timestamp": item.get("timestamp", "00:00"),
                "title": item.get("title", ""),
                "content": item.get("content", ""),
            }
            for item in (data.get("sections") or [])
            if isinstance(item, dict)
        ],
        "topics": [str(v) for v in (data.get("topics") or [])],
        "content_type": data.get("content_type") or "other",
        "target_audience": data.get("target_audience") or "",
        "tone": data.get("tone") or "",
        "mentions": [str(v) for v in (data.get("mentions") or [])],
        "notable_quotes": [str(v) for v in (data.get("notable_quotes") or [])],
    }


def _format_timestamp(seconds: float | int | None) -> str:
    total = max(0, int(seconds or 0))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
