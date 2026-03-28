"""Gemini API client - refactored from scripts/gemini_client.py."""

from google import genai
from google.genai import types


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
  "notable_quotes": ["Paraphrased key statements from the video — do NOT use direct quotes, rewrite in your own words (at least 3)"]
}

Important:
- summary_bullets should condense the video's main flow into 4-6 items. Fewer than sections, focusing only on key points.
- sections should be split wherever the topic changes in the video's actual flow. Even short videos should have at least 5 sections; longer videos (20+ min) should have 10 or more.
- If sections content contains double quotes ("), they MUST be escaped (\\"). Be careful not to break the JSON.
- notable_quotes must be paraphrased summaries of what was said, NOT verbatim transcriptions. Never use direct quotes.
"""

RESOLUTION_MAP = {
    "low": "MEDIA_RESOLUTION_LOW",
    "medium": "MEDIA_RESOLUTION_MEDIUM",
    "high": "MEDIA_RESOLUTION_HIGH",
}


class GeminiClient:
    """Wrapper around the Gemini API for analyzing YouTube videos."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0

    def analyze_video(self, video_id: str, prompt: str | None = None, media_resolution: str = "low") -> str:
        url = f"https://www.youtube.com/watch?v={video_id}"
        video_part = types.Part(file_data=types.FileData(file_uri=url))
        resolution = RESOLUTION_MAP.get(media_resolution, "MEDIA_RESOLUTION_LOW")

        response = self.client.models.generate_content(
            model=self.model,
            contents=[video_part, prompt or ANALYSIS_PROMPT],
            config=types.GenerateContentConfig(
                media_resolution=resolution,
                response_mime_type="application/json",
            ),
        )

        self.call_count += 1
        if response.usage_metadata:
            self.total_input_tokens += response.usage_metadata.prompt_token_count or 0
            self.total_output_tokens += response.usage_metadata.candidates_token_count or 0

        return response.text

    def generate_text(self, prompt: str) -> str:
        """Generate text-only content (no video input)."""
        response = self.client.models.generate_content(
            model=self.model, contents=[prompt],
        )

        self.call_count += 1
        if response.usage_metadata:
            self.total_input_tokens += response.usage_metadata.prompt_token_count or 0
            self.total_output_tokens += response.usage_metadata.candidates_token_count or 0

        return response.text

    def summary(self) -> str:
        total = self.total_input_tokens + self.total_output_tokens
        return (
            f"Gemini API: {self.call_count} calls, "
            f"{self.total_input_tokens:,} input + {self.total_output_tokens:,} output = "
            f"{total:,} total tokens"
        )
