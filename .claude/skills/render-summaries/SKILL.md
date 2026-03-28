---
name: render-summaries
description: Converts Gemini per-video summary JSON files into readable markdown and saves them to output/{handle}/summaries/
user-invocable: true
argument-hint: "@handle"
allowed-tools: Bash, Read, Glob
---

# Render Summaries Skill

Usage: `/render-summaries @handle`

## Instructions

When the user invokes this skill with `$ARGUMENTS`:

1. **Parse Handle**: Extract the handle from `$ARGUMENTS` (strip @ and URL prefix).

2. **Pre-check**: Check if `data/{handle}/raw/summaries/` exists and has JSON files.
   - If NOT: Tell the user to run `/summarize-videos @{handle}` or `/channel-analyze @{handle}` first.
   - If YES: Proceed to step 3.

3. **Run Rendering**:
   ```
   .venv/bin/python -m scripts.render_summaries @{handle}
   ```

4. **Verify Results**:
   - Count files in `output/{handle}/summaries/`
   - Report how many were rendered vs skipped

5. **Report Results**: Tell the user the output path and list the rendered files.

## Notes
- Already-rendered files are automatically skipped on re-run
- To re-render a video, delete its `.md` file from `output/{handle}/summaries/`
- Source JSON is preserved in `data/{handle}/raw/summaries/`
