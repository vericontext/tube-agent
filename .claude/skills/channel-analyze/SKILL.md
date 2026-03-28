---
name: channel-analyze
description: Takes a YouTube channel handle or URL, collects recent video data, and runs analysis agents
user-invocable: true
argument-hint: "@handle or YouTube URL"
allowed-tools: Bash, Read, Glob, Grep, Agent
---

# Channel Analyze Skill

Usage: `/channel-analyze @handle` or `/channel-analyze https://youtube.com/@handle`

## Instructions

When the user invokes this skill with a YouTube channel handle or URL via `$ARGUMENTS`:

1. **Parse Handle**: Extract the @handle from `$ARGUMENTS`. Strip any URL prefix if provided (e.g., `https://youtube.com/@eo_korea` → `eo_korea`).

2. **Collect Data**: Run the data fetcher agent to collect channel data:
   - Use the Agent tool with subagent_type `data-fetcher` (defined in `.claude/agents/data-fetcher.md`)
   - Pass the handle and instruct it to run `.venv/bin/python -m scripts.fetch_all @{handle}`

3. **Render Summaries**: After data collection completes, render Gemini video summaries to readable markdown:
   ```
   .venv/bin/python -m scripts.render_summaries @{handle}
   ```
   This converts `data/{handle}/raw/summaries/*.json` → `output/{handle}/summaries/*.md`.

4. **Run Analysis Agents in Parallel**: After data collection and summary rendering complete, launch 4 analysis agents in parallel using the Agent tool. **Include the handle in each agent's prompt** so they know where to find the data (e.g., "Channel handle: {handle}"):
   - `content-analyzer` agent (subagent_type) → analyzes videos + summaries
   - `comment-analyzer` agent (subagent_type) → analyzes comments
   - `trend-analyzer` agent (subagent_type) → analyzes trends
   - `summary-analyzer` agent (subagent_type) → analyzes Gemini video summaries

   All four should run with `run_in_background: true` for parallel execution.

5. **Summarize Results**: Once all agents complete, read the analysis outputs from `output/{handle}/` and present a brief summary of key findings to the user in English.

## Notes
- The venv must exist at `.venv/`. If it doesn't, create it first.
- All reports are written in English.
- Data is saved to `data/{handle}/`, analysis to `output/{handle}/`.
