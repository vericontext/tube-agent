# Tube Agent

YouTube channel transcript indexing and AI-powered video analysis system.

Collects channel metadata, video lists, and timestamped transcripts so trusted YouTube channels can be searched quickly. Gemini summaries, comments, and reports remain available as optional deeper analysis.

## Setup

```bash
# 1. Create Python virtual environment and install packages
python3 -m venv .venv
.venv/bin/pip install -e .

# 2. Configure API keys
cp .env.example .env
# Add the following keys to the .env file:
#   YOUTUBE_API_KEY=...   (from Google Cloud Console)
#   GEMINI_API_KEY=...    (from Google AI Studio)
```

## Pipeline: Step-by-Step

The full pipeline runs with a single command:

```bash
.venv/bin/python -m scripts.fetch_all @channel_handle
```

Below is a detailed breakdown of what happens at each stage.

---

### Stage 1: Channel Metadata Collection

**What it does**: Calls the YouTube Data API `channels` endpoint with `forHandle` to retrieve the channel's core information.

**How it works**:
1. Sends a request to `GET /youtube/v3/channels?forHandle={handle}&part=snippet,contentDetails,statistics,brandingSettings`
2. Extracts from the response:
   - **snippet**: channel title, description, country, published date
   - **statistics**: subscriber count, total view count, total video count
   - **contentDetails**: the `uploads` playlist ID (needed for Stage 2)
3. Saves two files via the storage backend:
   - `data/{handle}/raw/channel.json` — the raw API response
   - `data/{handle}/processed/channel_summary.json` — a cleaned, flattened version with numeric fields parsed

**API quota cost**: 1 unit

**Output example** (channel_summary.json):
```json
{
  "id": "UCkMrp1Nh7JBilHNjgrewStQ",
  "handle": "eo_korea",
  "title": "EO",
  "subscriber_count": 2150000,
  "view_count": 845000000,
  "video_count": 1200,
  "published_at": "2017-03-15T00:00:00Z"
}
```

---

### Stage 2: Video List Collection

**What it does**: Fetches the channel's uploaded videos with full metadata (title, stats, duration, tags).

**How it works**:
1. Uses the `uploads` playlist ID from Stage 1
2. Calls `GET /youtube/v3/playlistItems?playlistId={id}&part=snippet&maxResults=50` with pagination (50 items per page, using `nextPageToken`) until `--max-videos` is reached
3. Collects all video IDs from the playlist response
4. Calls `GET /youtube/v3/videos?id={comma-separated-ids}&part=snippet,contentDetails,statistics` in batches of 50 to get detailed metadata for each video
5. For each video, computes enriched fields:
   - `durationSeconds`: ISO 8601 duration (`PT1H2M3S`) parsed to seconds
   - `viewCountFormatted`: human-readable format (`1.2M`, `45.3K`)
   - `likeRatio`: `likeCount / viewCount`
   - `commentRatio`: `commentCount / viewCount`
6. Saves the enriched video list to `data/{handle}/processed/videos_enriched.json`

**API quota cost**: 1 unit per page of playlist items + 1 unit per batch of 50 video details

**Output**: A JSON array where each element contains:
```json
{
  "videoId": "abc123",
  "title": "Video Title",
  "publishedAt": "2024-01-15T09:00:00Z",
  "tags": ["startup", "tech"],
  "duration": "PT25M30S",
  "durationSeconds": 1530,
  "viewCount": 1250000,
  "viewCountFormatted": "1.3M",
  "likeCount": 45000,
  "commentCount": 1200,
  "likeRatio": 0.036,
  "commentRatio": 0.00096
}
```

---

### Stage 3: Comment Collection

**What it does**: Fetches top-level comments for each video. Skippable with `--skip-comments`.

**How it works**:
1. Iterates through all videos from Stage 2
2. For each video, checks `storage.has_comments(video_id)` — **skips if already collected** (idempotent)
3. Calls `GET /youtube/v3/commentThreads?videoId={id}&part=snippet&maxResults=100&order=relevance&textFormat=plainText`
4. Extracts from each comment thread:
   - `author`: display name
   - `text`: comment text (plain text, not HTML)
   - `likeCount`: number of likes on the comment
   - `publishedAt`: comment timestamp
5. Saves to `data/{handle}/raw/comments/{videoId}.json`
6. If the API returns 403 (comments disabled), silently skips that video

**API quota cost**: 1 unit per video

**Skip behavior**: Already-fetched comments are never re-downloaded. To refresh, delete the individual JSON file and re-run.

---

### Stage 4: Gemini Video Analysis (Summaries)

**What it does**: Sends each YouTube video URL directly to the Gemini API for multimodal analysis. Gemini watches the video (frames + audio) and produces a structured JSON summary. Skippable with `--skip-summaries`.

**How it works**:
1. Selects videos to analyze: all videos, or limited by `--summary-max N`
2. For each video, checks `storage.has_summary(video_id)` — **skips if already analyzed**
3. Constructs the Gemini API request:
   - **Model**: `gemini-2.5-flash`
   - **Input**: YouTube video URL as a `FileData` part (Gemini downloads and processes the video internally)
   - **Media resolution**: configurable via `--media-resolution low|medium|high` (affects token count and cost)
   - **Prompt**: A detailed analysis prompt requesting structured JSON output
4. Gemini processes the video multimodally:
   - Samples video frames at the specified resolution
   - Processes audio/speech
   - Returns analysis as a JSON string
5. Parses the response:
   - Strips markdown fences if present (` ```json ... ``` `)
   - Handles control characters that would break JSON parsing
   - Falls back to regex-based JSON repair if initial parse fails
6. Saves to `data/{handle}/raw/summaries/{videoId}.json`
7. Waits 2 seconds between API calls (rate limiting)

**Token cost**: ~100K-180K input tokens per video at `low` resolution. Higher resolutions use more tokens.

**Output structure** (per video):
```json
{
  "videoId": "abc123",
  "title": "Video Title",
  "analysis": {
    "summary_intro": "Speaker intro + topic overview (3-4 sentences)",
    "summary_bullets": [
      {
        "title": "Key Point Title",
        "timestamp": "03:45",
        "description": "2-3 sentence summary of this key point"
      }
    ],
    "sections": [
      {
        "timestamp": "00:00",
        "title": "Section Title",
        "content": "Detailed 3-5+ sentence description of this segment"
      }
    ],
    "topics": ["startup", "fundraising", "product-market-fit"],
    "content_type": "interview",
    "target_audience": "Aspiring entrepreneurs and startup founders",
    "tone": "educational",
    "mentions": ["Y Combinator", "Paul Graham"],
    "notable_quotes": ["Direct quote from the video"]
  }
}
```

**Three levels of reading depth**:
- **summary_intro + summary_bullets**: Quick overview (~1 min read)
- **sections**: Full detailed walkthrough (~5 min read)
- **Watch the video**: Original source

---

### Stage 5: Channel Report Generation

**What it does**: Aggregates all collected data and generates a comprehensive markdown report using Gemini. Runs automatically after summaries unless `--skip-report` is set.

**How it works**:
1. Reads channel metadata from storage
2. Loads all videos sorted by view count (up to 200)
3. Collects AI summaries for the top 50 videos
4. Aggregates statistics:
   - **Top/bottom performing videos** (by view count)
   - **Average engagement metrics** (views, likes, comments, ratios)
   - **Topic distribution** from summary `topics` fields
   - **Content type distribution** (interview, lecture, tutorial, etc.)
   - **Monthly upload frequency** from video publish dates
   - **Summary intros** (first 300 chars each, up to 30 videos)
5. Sends the aggregated JSON payload to Gemini with a report generation prompt
6. Gemini produces a markdown report covering:
   - Channel Overview
   - Content Strategy
   - Performance Analysis
   - Trend Analysis
   - Summary-Based Insights
   - Recommendations
7. Saves to `output/{handle}/reports/channel_overview.md`

---

## Storage Backends

Data flows through a storage abstraction layer:

| Backend | Primary Use | When Active |
|---------|------------|-------------|
| **LocalStorage** | JSON files on disk | CLI default when `DATABASE_URL` is unset |
| **PostgresStorage** | SQLAlchemy ORM (works with SQLite or Postgres) | When `DATABASE_URL` starts with `sqlite` or `postgresql` (SQLite is the default) |

---

## CLI Options

```bash
.venv/bin/python -m scripts.fetch_all @channel_handle [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--max-videos N` | 100 | Maximum number of videos to fetch |
| `--with-comments` | false | Fetch comments |
| `--with-summaries` | false | Run Gemini video analysis |
| `--skip-transcripts` | false | Skip transcript indexing |
| `--transcript-languages` | `ko,en` | Comma-separated transcript language priority |
| `--skip-report` | false | Skip report generation (Stage 5) |
| `--summary-max N` | all | Limit how many videos Gemini analyzes |
| `--media-resolution` | low | Gemini video resolution: `low`, `medium`, `high` |

### Examples

```bash
# Quick test: index transcripts for 20 videos
.venv/bin/python -m scripts.fetch_all @eo_korea --max-videos 20

# Include Gemini summaries for 10 videos
.venv/bin/python -m scripts.fetch_all @eo_korea \
  --with-summaries --summary-max 10

# Include comments and Gemini summaries
.venv/bin/python -m scripts.fetch_all @eo_korea \
  --with-comments --with-summaries --summary-max 50
```

## API Server Mode

```bash
.venv/bin/tube-api --reload
```

The pipeline runs in-process via FastAPI `BackgroundTasks`; no Redis or Celery worker required. Data is persisted to `./tube_agent.db` (SQLite) by default — override with `DATABASE_URL` to point at Postgres.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/channels` | Start channel analysis pipeline (runs in background) |
| GET | `/api/v1/channels` | List channels |
| GET | `/api/v1/channels/{handle}` | Channel details |
| GET | `/api/v1/channels/{handle}/videos` | Video list (sort/filter/paginate) |
| GET | `/api/v1/channels/{handle}/videos/{id}/summary` | Video summary |
| GET | `/api/v1/channels/{handle}/videos/{id}/transcript` | Timestamped transcript |
| GET | `/api/v1/channels/{handle}/reports` | List reports |
| GET | `/api/v1/channels/{handle}/reports/{type}` | Get report |
| GET | `/api/v1/search?q=keyword` | Search videos/summaries/transcripts |
| GET | `/api/v1/jobs/{id}` | Job status |
| GET | `/health` | Health check |

## Claude Code Integration

Skills and agents are available in Claude Code:

```
/channel-analyze @channel_handle    Collect data + run 4 analysis agents in parallel
/summarize-videos @channel_handle   Run Gemini video analysis only
/channel-report                     Generate a comprehensive English report from analysis results
```

## Project Structure

```
scripts/
  fetch_all.py          CLI orchestrator (entry point)

tube_agent/
  config.py             Settings from environment variables
  services/
    youtube.py          YouTube Data API v3 client (httpx)
    gemini.py           Gemini API client (multimodal video analysis)
    pipeline.py         Pipeline orchestration (shared by CLI and API)
    report.py           Channel report generation
  storage/
    base.py             StorageBackend ABC
    local.py            JSON file storage
    postgres.py         SQLAlchemy ORM (SQLite or Postgres)
  api/                  FastAPI endpoints (BackgroundTasks-based)
  migrations/           JSON → DB migration scripts

data/{handle}/
  raw/                  Raw API responses
    channel.json
    videos.json
    comments/{videoId}.json
    summaries/{videoId}.json
  processed/            Enriched data
    channel_summary.json
    videos_enriched.json

output/{handle}/
  reports/              Generated analysis reports
    channel_overview.md
```
