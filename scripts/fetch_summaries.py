"""Fetch per-video content summaries using Gemini API."""

import json
import time

from scripts.gemini_client import GeminiClient
from scripts.utils import save_json

ANALYSIS_PROMPT = """\
Watch this YouTube video from start to finish and analyze it in detail — thorough enough that a reader wouldn't need to watch the video.
Respond ONLY with valid JSON (no markdown fences).

{
  "summary_intro": "Introduce the speaker(s) (name, title, key background) and the video topic in 3-4 sentences. End with 'Here are the key takeaways.'",
  "summary_bullets": [
    {
      "title": "Subtitle (e.g., Key Lessons from Silicon Valley)",
      "timestamp": "MM:SS",
      "description": "Summarize the key content of this topic in 2-3 sentences. Include specific claims, examples, and advice."
    }
  ],
  "sections": [
    {
      "timestamp": "MM:SS",
      "title": "Section subtitle",
      "content": "Describe the content covered in this segment in detail. Include the speaker's key arguments, supporting evidence, specific examples and anecdotes, and any data or numbers mentioned. Write at least 3-5 sentences; write more for content-rich segments."
    }
  ],
  "topics": ["topic1", "topic2"],
  "content_type": "interview | lecture | vlog | documentary | review | tutorial | entertainment | other",
  "target_audience": "Description of the target audience",
  "tone": "serious | humorous | educational | inspirational | casual | formal",
  "mentions": ["People, brands, or organizations mentioned"],
  "notable_quotes": ["Direct quotes of notable statements from the video (at least 3)"]
}

Important:
- summary_bullets should condense the video's main flow into 4-6 items. Fewer than sections, focusing only on key points.
- sections should be split wherever the topic changes in the video's actual flow. Even short videos should have at least 5 sections; longer videos (20+ min) should have 10 or more.
- If sections content contains double quotes ("), they MUST be escaped (\\\"). Be careful not to break the JSON.
"""


def fetch_summaries(
    videos: list[dict],
    paths: dict,
    max_videos: int | None = None,
    media_resolution: str = "low",
    delay: float = 2.0,
) -> dict[str, bool]:
    """Analyze videos with Gemini. Returns {video_id: success}."""
    target = videos[:max_videos] if max_videos else videos
    print(f"Analyzing {len(target)} videos with Gemini (resolution={media_resolution})...")

    client = GeminiClient()
    results = {}
    success_count = 0
    skipped_count = 0
    summaries_dir = paths["raw"] / "summaries"

    for i, video in enumerate(target, 1):
        vid = video["videoId"]
        out_path = summaries_dir / f"{vid}.json"

        # Skip if already analyzed
        if out_path.exists():
            results[vid] = True
            skipped_count += 1
            continue

        try:
            raw_text = client.analyze_video(vid, ANALYSIS_PROMPT, media_resolution)

            # Parse JSON from response
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            try:
                analysis = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try fixing common JSON issues
                import re
                fixed = cleaned
                # Fix invalid \' escape (not valid in JSON, but Gemini sometimes uses it)
                fixed = fixed.replace("\\'", "'")
                # Replace control chars (except \n, \r, \t which are structural)
                fixed = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', lambda m: f'\\u{ord(m.group()):04x}', fixed)
                analysis = json.loads(fixed)

            save_json(
                {"videoId": vid, "title": video.get("title", ""), "analysis": analysis},
                out_path,
            )
            results[vid] = True
            success_count += 1

        except Exception as e:
            save_json(
                {"videoId": vid, "title": video.get("title", ""), "error": str(e)},
                out_path,
            )
            results[vid] = False
            print(f"  Error analyzing {vid}: {e}")

        if i % 5 == 0 or i == len(target):
            print(f"  Progress: {i}/{len(target)} ({success_count} OK, {skipped_count} skipped)")

        # Rate limit
        if i < len(target):
            time.sleep(delay)

    # Build summary index
    _build_index(summaries_dir, paths)

    print(f"  Summaries: {success_count} new, {skipped_count} skipped")
    print(f"  {client.summary()}")
    return results


def _build_index(summaries_dir, paths):
    """Build a lightweight index of all summaries."""
    index = []
    for path in sorted(summaries_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = {
            "videoId": data.get("videoId"),
            "title": data.get("title", ""),
            "has_analysis": "analysis" in data,
        }
        if "analysis" in data:
            entry["summary_intro"] = data["analysis"].get("summary_intro", "")
            entry["topics"] = data["analysis"].get("topics", [])
            entry["content_type"] = data["analysis"].get("content_type", "")
            entry["section_count"] = len(data["analysis"].get("sections", []))
        index.append(entry)

    save_json(index, paths["processed"] / "summaries_index.json")
    print(f"  Index: {len(index)} entries written to summaries_index.json")
