---
name: summarize-videos
description: Runs Gemini API multimodal analysis on YouTube videos to extract summaries, topics, tone, and more
user-invocable: true
argument-hint: "@handle [--max 10] [--resolution low|medium|high]"
allowed-tools: Bash, Read, Glob, Grep, Agent
---

# Summarize Videos Skill

Usage: `/summarize-videos @handle` or `/summarize-videos @handle --max 10 --resolution medium`

## Instructions

When the user invokes this skill with `$ARGUMENTS`:

1. **Parse Arguments**: Extract from `$ARGUMENTS`:
   - `handle` (required): YouTube channel handle (strip @ and URL prefix)
   - `--max N` (optional, default 10): Number of videos to analyze
   - `--resolution` (optional, default "low"): Media resolution (low/medium/high)

2. **Pre-check**: Check if `data/{handle}/raw/videos.json` exists.
   - If NOT: Tell the user to run `/channel-analyze @{handle}` first, or offer to run data collection.
   - If YES: Proceed to step 3.

3. **Run Gemini Analysis**: Run the summarize command:
   ```
   .venv/bin/python -m scripts.fetch_all @{handle} --skip-comments --summary-max {max} --media-resolution {resolution}
   ```

4. **Verify Results**:
   - Count files in `data/{handle}/raw/summaries/`
   - Read `data/{handle}/processed/summaries_index.json` to verify index was generated
   - Report success count and any errors

5. **Run Analysis** (optional): If the user requested analysis, launch the `summary-analyzer` agent (with handle in prompt) to generate `output/{handle}/summary_analysis.md`.

6. **Summarize Results**: Present a brief English summary of what was analyzed, including:
   - Number of videos analyzed
   - Common topics found
   - Gemini token usage (from command output)

## Notes
- Requires `GEMINI_API_KEY` in `.env`
- `low` resolution is cheapest (100 tokens/sec, 1/3 of default)
- Already-analyzed videos are automatically skipped on re-run
- To re-analyze a video, delete its file from `data/{handle}/raw/summaries/`
