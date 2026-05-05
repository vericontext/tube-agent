"""YouTube transcript extraction via yt-dlp subtitle metadata."""

from __future__ import annotations

import html
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import httpx
import yt_dlp


@dataclass(frozen=True)
class TranscriptResult:
    video_id: str
    language: str
    source: str
    segments: list[dict]


class TranscriptUnavailableError(RuntimeError):
    """Raised when no usable caption track is available for a video."""


class TranscriptExtractor:
    """Extract caption-backed YouTube transcripts and normalize them into readable chunks."""

    def __init__(
        self,
        languages: list[str] | None = None,
        timeout: float = 20.0,
        retries: int = 2,
        retry_backoff: float = 2.0,
    ):
        self.languages = languages or ["ko", "en"]
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff

    def extract(self, video_id: str) -> TranscriptResult:
        info = self._extract_info(video_id)
        track = self._select_track(info)
        raw_segments = self._fetch_track(track["url"], track.get("ext", ""))
        segments = _merge_segments(raw_segments)
        if not segments:
            raise TranscriptUnavailableError(f"No usable transcript text for {video_id}")
        return TranscriptResult(
            video_id=video_id,
            language=track["language"],
            source=track["source"],
            segments=segments,
        )

    def _extract_info(self, video_id: str) -> dict[str, Any]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": self.languages,
            "subtitlesformat": "json3/vtt/srv3/srv2/srv1/best",
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as exc:
            raise TranscriptUnavailableError(f"Unable to inspect subtitles for {video_id}: {exc}") from exc

    def _select_track(self, info: dict[str, Any]) -> dict[str, str]:
        """Pick the best caption track for this video.

        Priority order:
          1. Manual subs in any preferred language.
          2. Auto-generated *source* captions in any preferred language
             (URL has no ``tlang=``).
          3. Auto-translated captions to a preferred language (URL has
             ``tlang=``) — last resort, since YouTube rate-limits the
             translation endpoint aggressively.
        """
        subtitles = info.get("subtitles") or {}
        automatic = info.get("automatic_captions") or {}

        for language in self.languages:
            selected = _find_language_track(subtitles, language)
            if selected:
                selected["source"] = "manual"
                return selected

        for language in self.languages:
            selected = _find_language_track(automatic, language)
            if selected and "tlang=" not in selected["url"]:
                selected["source"] = "auto"
                return selected

        for language in self.languages:
            selected = _find_language_track(automatic, language)
            if selected:
                selected["source"] = "auto-translated"
                return selected

        raise TranscriptUnavailableError("No matching transcript language found")

    def _fetch_track(self, url: str, ext: str) -> list[dict]:
        with httpx.Client(follow_redirects=True, timeout=self.timeout) as client:
            for attempt in range(self.retries + 1):
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    body = response.text
                    break
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    if status_code == 429 and attempt < self.retries:
                        time.sleep(_retry_delay(exc.response, attempt, self.retry_backoff))
                        continue
                    if status_code == 429:
                        raise TranscriptUnavailableError(
                            "YouTube transcript endpoint rate-limited this device/network (HTTP 429). "
                            "Try again later or index fewer videos at once."
                        ) from exc
                    raise TranscriptUnavailableError(
                        f"Unable to fetch transcript track (HTTP {status_code})"
                    ) from exc
                except httpx.HTTPError as exc:
                    if attempt < self.retries:
                        time.sleep(self.retry_backoff * (attempt + 1))
                        continue
                    raise TranscriptUnavailableError(f"Unable to fetch transcript track: {exc}") from exc
            else:
                raise TranscriptUnavailableError("Unable to fetch transcript track")
        if ext == "json3" or body.lstrip().startswith("{"):
            return _parse_json3(body)
        if ext.startswith("srv") or body.lstrip().startswith("<"):
            return _parse_xml(body)
        return _parse_vtt(body)


def _find_language_track(collection: dict[str, list[dict]], desired_language: str) -> dict[str, str] | None:
    candidates = []
    if desired_language in collection:
        candidates.append((desired_language, collection[desired_language]))
    for language, tracks in collection.items():
        if language != desired_language and language.startswith(f"{desired_language}-"):
            candidates.append((language, tracks))

    for language, tracks in candidates:
        track = _best_track(tracks)
        if track and track.get("url"):
            return {
                "language": language,
                "url": track["url"],
                "ext": track.get("ext", ""),
            }
    return None


def _best_track(tracks: list[dict]) -> dict | None:
    preference = {"json3": 0, "srv3": 1, "srv2": 2, "srv1": 3, "vtt": 4}
    usable = [track for track in tracks if track.get("url")]
    if not usable:
        return None
    return sorted(usable, key=lambda track: preference.get(track.get("ext", ""), 99))[0]


def _retry_delay(response: httpx.Response, attempt: int, fallback: float) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 60.0)
        except ValueError:
            pass
    return fallback * (attempt + 1)


def _parse_json3(body: str) -> list[dict]:
    data = json.loads(body)
    segments = []
    for event in data.get("events", []):
        text = _clean_text("".join(seg.get("utf8", "") for seg in event.get("segs", [])))
        if not text:
            continue
        start = (event.get("tStartMs") or 0) / 1000
        duration = (event.get("dDurationMs") or 0) / 1000
        segments.append({
            "start_seconds": start,
            "end_seconds": start + duration,
            "text": text,
        })
    return segments


def _parse_xml(body: str) -> list[dict]:
    root = ET.fromstring(body)
    segments = []
    for elem in root.iter():
        if elem.tag.split("}")[-1] not in {"text", "p"}:
            continue
        text = _clean_text("".join(elem.itertext()))
        if not text:
            continue
        start = float(elem.attrib.get("start", elem.attrib.get("t", 0)) or 0)
        duration = float(elem.attrib.get("dur", elem.attrib.get("d", 0)) or 0)
        if "t" in elem.attrib:
            start = start / 1000
        if "d" in elem.attrib:
            duration = duration / 1000
        segments.append({
            "start_seconds": start,
            "end_seconds": start + duration,
            "text": text,
        })
    return segments


def _parse_vtt(body: str) -> list[dict]:
    segments = []
    current_start = None
    current_end = None
    current_lines = []

    def flush():
        nonlocal current_start, current_end, current_lines
        if current_start is not None:
            text = _clean_text(" ".join(current_lines))
            if text:
                segments.append({
                    "start_seconds": current_start,
                    "end_seconds": current_end or current_start,
                    "text": text,
                })
        current_start = None
        current_end = None
        current_lines = []

    for line in body.splitlines():
        line = line.strip()
        if not line:
            flush()
            continue
        if line == "WEBVTT" or line.startswith(("NOTE", "STYLE", "REGION")):
            continue
        if "-->" in line:
            flush()
            start_raw, end_raw = line.split("-->", 1)
            current_start = _parse_vtt_time(start_raw.strip())
            current_end = _parse_vtt_time(end_raw.split()[0].strip())
            continue
        if current_start is not None and not line.isdigit():
            current_lines.append(line)
    flush()
    return segments


def _parse_vtt_time(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2]) if len(parts) >= 2 else 0
    hours = int(parts[-3]) if len(parts) >= 3 else 0
    return hours * 3600 + minutes * 60 + seconds


def _merge_segments(segments: list[dict], max_chars: int = 520, max_gap: float = 4.0) -> list[dict]:
    merged = []
    current = None
    for segment in segments:
        text = segment.get("text", "")
        if not text:
            continue
        start = float(segment.get("start_seconds", 0.0))
        end = float(segment.get("end_seconds", start))
        if (
            current
            and start - current["end_seconds"] <= max_gap
            and len(current["text"]) + len(text) + 1 <= max_chars
        ):
            current["text"] = f"{current['text']} {text}"
            current["end_seconds"] = max(current["end_seconds"], end)
            continue
        if current:
            merged.append(current)
        current = {
            "start_seconds": start,
            "end_seconds": end,
            "text": text,
        }
    if current:
        merged.append(current)
    return merged


def _clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\n", " ")
    return re.sub(r"\s+", " ", value).strip()
