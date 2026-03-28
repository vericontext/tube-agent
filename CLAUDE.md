# Tube Agent - YouTube Channel Analysis System

## Setup
- Python venv: `.venv`
- Install: `python -m venv .venv && .venv/bin/pip install -e .`
- API keys: set `YOUTUBE_API_KEY`, `GEMINI_API_KEY` in `.env`
- Database: set `DATABASE_URL` in `.env` (PostgreSQL)

## Running

### CLI Mode (original)
- Data collection: `.venv/bin/python -m scripts.fetch_all @handle`
- Flags: `--skip-comments`, `--skip-summaries`, `--max-videos 100`, `--summary-max N`

### API Server Mode
- Start: `.venv/bin/tube-api --reload` or `uvicorn tube_agent.api.main:app --reload`
- Docker: `docker-compose up` (starts API + PostgreSQL + Redis + Celery worker)

### Data Migration
- JSON → PostgreSQL: `.venv/bin/tube-migrate --all` or `--handle ycombinator`

## Architecture

### Packages
- `scripts/` — Original CLI data collection scripts (unchanged)
- `tube_agent/` — Production SaaS package
  - `tube_agent/models/` — Pydantic schemas + SQLAlchemy ORM
  - `tube_agent/storage/` — Storage abstraction (LocalStorage, PostgresStorage)
  - `tube_agent/services/` — YouTube client, Gemini client, pipeline orchestration
  - `tube_agent/api/` — FastAPI endpoints
  - `tube_agent/tasks/` — Celery async task definitions
  - `tube_agent/migrations/` — JSON → DB migration scripts

### Storage Abstraction
- `StorageBackend` ABC with `LocalStorage` (JSON files) and `PostgresStorage` (SQLAlchemy)
- CLI uses `LocalStorage`, API uses `PostgresStorage`
- Shared data (channels/videos/summaries) is tenant-independent

### Data Structure (CLI mode)
Data is organized per channel handle:
- `data/{handle}/raw/` - Raw API responses (channel.json, videos.json, comments/, summaries/)
- `data/{handle}/processed/` - Enriched/summarized data
- `output/{handle}/` - Analysis results and reports
- `output/{handle}/reports/` - Generated reports

Transcripts, comments, and summaries support skip logic — already-fetched files are not re-downloaded on re-run.

## API Endpoints
- `POST /api/v1/channels` — Start channel analysis pipeline
- `GET  /api/v1/channels` — List channels
- `GET  /api/v1/channels/{handle}` — Channel details
- `GET  /api/v1/channels/{handle}/videos` — Video list (sort/filter/paginate)
- `GET  /api/v1/channels/{handle}/videos/{id}/summary` — Video summary
- `GET  /api/v1/channels/{handle}/reports` — List reports
- `GET  /api/v1/channels/{handle}/reports/{type}` — Get report
- `GET  /api/v1/search?q=keyword` — Search videos/summaries
- `GET  /api/v1/jobs/{id}` — Job status
- `GET  /health` — Health check

## Conventions
- All reports are written in English
- Python scripts are in `scripts/` package
- Sub-agents in `.claude/agents/`, Skills in `.claude/skills/`
