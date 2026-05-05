# Tube Agent

Local-first desktop app for indexing YouTube channel transcripts and searching them by keyword + semantic meaning. SQLite + fastembed (ONNX) on-device, optional Gemini multimodal analysis layered on top.

## Run

```bash
# CLI / API (headless)
.venv/bin/python -m scripts.fetch_all @handle    # index a channel
.venv/bin/tube-api --reload                       # FastAPI on :8000

# Desktop (Tauri)
cd desktop && npm run tauri dev                   # dev: spawns sidecar from .venv
cd desktop && bash scripts/build.sh               # release: PyInstaller + tauri build
```

Tests: `.venv/bin/pytest tests/ -q`

## Layout

- `tube_agent/` — Python core
  - `services/pipeline.py` — orchestrates the full pipeline (called by CLI + API + sidecar)
  - `services/embeddings.py` — `EmbeddingProvider` ABC + Fastembed (default) + Gemini
  - `services/transcripts.py` — yt-dlp caption extractor
  - `storage/postgres.py` — SQLAlchemy ORM (works with SQLite or Postgres despite the name)
  - `api/main.py` + `api/routes/` — FastAPI endpoints
  - `cli_sidecar.py` — Tauri sidecar entry (uvicorn programmatic runner)
  - `config.py` — `Settings.resolve_app_data_dir()` returns `~/Library/Application Support/tube-agent` (mac default)
- `scripts/fetch_all.py` — CLI orchestrator
- `desktop/` — Tauri 2 + Vite + React 19 + shadcn (see `desktop/README.md`)
- `tests/` — pytest, in-memory SQLite via `StaticPool`

## Conventions

- Default flow indexes transcripts only. Comments + Gemini summaries are opt-in (`--with-comments`, `--with-summaries`).
- `APP_DATA_DIR=/path` overrides the per-OS default; `DATABASE_URL=...` overrides the derived SQLite path.
- New code goes through the API + storage abstractions — don't write directly to disk from the routes.
- Reports / generated docs are written in English.
- All settings flow through `tube_agent/config.py` and `pydantic-settings` (`extra="ignore"` so legacy `.env` keys are tolerated).

## Memory of past work (recent)

- Cloud removal pivot: dropped Supabase/Celery/Redis/R2/Fly.io. Multi-tenant schema removed in a follow-up.
- Caption-based indexing (yt-dlp) is the primary path; Gemini multimodal is opt-in and slow/expensive.
- Local semantic search uses fastembed `paraphrase-multilingual-MiniLM-L12-v2` (220 MB, downloaded on first run).
- Tauri release builds spawn the sidecar as a process group so children get cleaned up on quit.
