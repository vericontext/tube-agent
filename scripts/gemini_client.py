"""Gemini API client wrapper for video analysis."""

import os

from google import genai
from google.genai import types


class GeminiClient:
    """Wrapper around the Gemini API for analyzing YouTube videos."""

    def __init__(self, api_key: str | None = None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        self.client = genai.Client(api_key=key)
        self.model = "gemini-2.5-flash"
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0

    RESOLUTION_MAP = {
        "low": "MEDIA_RESOLUTION_LOW",
        "medium": "MEDIA_RESOLUTION_MEDIUM",
        "high": "MEDIA_RESOLUTION_HIGH",
    }

    def analyze_video(
        self,
        video_id: str,
        prompt: str,
        media_resolution: str = "low",
    ) -> str:
        """Analyze a YouTube video using Gemini's multimodal capabilities."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        video_part = types.Part(
            file_data=types.FileData(file_uri=url)
        )
        resolution = self.RESOLUTION_MAP.get(media_resolution, "MEDIA_RESOLUTION_LOW")

        response = self.client.models.generate_content(
            model=self.model,
            contents=[video_part, prompt],
            config=types.GenerateContentConfig(
                media_resolution=resolution,
            ),
        )

        self.call_count += 1
        if response.usage_metadata:
            self.total_input_tokens += response.usage_metadata.prompt_token_count or 0
            self.total_output_tokens += response.usage_metadata.candidates_token_count or 0

        return response.text

    def summary(self) -> str:
        """Return usage summary string."""
        total = self.total_input_tokens + self.total_output_tokens
        return (
            f"Gemini API: {self.call_count} calls, "
            f"{self.total_input_tokens:,} input + {self.total_output_tokens:,} output = "
            f"{total:,} total tokens"
        )
