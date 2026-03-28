---
name: channel-report
description: Generates a comprehensive English report from analyzed data
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write
---

# Channel Report Skill

Usage: `/channel-report`

## Instructions

When the user invokes this skill, generate a comprehensive English report from the analyzed data.

1. **Parse Handle**: Extract the handle from `$ARGUMENTS` (strip @ and URL prefix). If no argument provided, look for the most recently modified channel directory under `data/`.

2. **Verify Data**: Read the following files (where `{handle}` is the channel handle):
   - `data/{handle}/processed/channel_summary.json` - Channel overview
   - `data/{handle}/processed/videos_enriched.json` - Video metadata
   - `output/{handle}/content_analysis.md` - Content analysis
   - `output/{handle}/comment_analysis.md` - Comment analysis
   - `output/{handle}/trend_analysis.md` - Trend analysis
   - `output/{handle}/summary_analysis.md` - Gemini summary analysis (if available)

3. **Generate Comprehensive Report**: Write a comprehensive report in English to `output/{handle}/reports/{handle}_{date}.md` using this structure:

```markdown
# YouTube Channel Analysis: {Channel Name}
> Generated: YYYY-MM-DD | Videos Analyzed: N

## 1. Channel Overview
(Subscribers, total views, video count, creation date, channel description)

## 2. Content Strategy Analysis
### Top 10 Performing Videos
### Content Category Classification
### Title Pattern Analysis
### Subtitle-Based Topic Analysis

## 3. Engagement Analysis
### Like/View Ratio
### Comment/View Ratio
### Optimal Video Length

## 4. Comment Insights
### Sentiment Distribution
### Viewer Requests & Questions
### Community Health

## 5. Trend Analysis
### Upload Frequency Trends
### View Count Growth Trajectory
### Topic Evolution

## 6. Deep Content Analysis (Gemini)
### Topic Distribution & Content Types
### Tone x Performance Cross-Analysis
### Mention Network
### Content Gap Analysis

## 7. Recommendations
(Data-driven actionable insights)
```

4. Synthesize insights from all three analysis files. Do not just copy-paste — integrate and cross-reference findings.

5. The `{handle}` comes from the argument or `channel_summary.json` and `{date}` is today's date (YYYY-MM-DD format).

6. After writing the report, tell the user the file path.
