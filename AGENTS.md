# Tube Agent — agent context

Local-first desktop app for indexing YouTube channel transcripts and searching them with keyword + semantic similarity. Python core (FastAPI + SQLite + fastembed + yt-dlp) packaged inside a Tauri 2 shell as a sidecar.

## Run / verify

```bash
# Python venv at .venv (already created)
.venv/bin/pytest tests/ -q                                    # 62+ tests, in-memory SQLite
.venv/bin/python -m scripts.fetch_all @handle                  # CLI indexing
.venv/bin/tube-api --reload                                    # FastAPI on :8000

# Desktop
cd desktop && npm run tauri dev                                # dev (spawns .venv sidecar)
cd desktop && bash scripts/build.sh                            # release (.app + .dmg)
```

## Where things live

| Path | Purpose |
|---|---|
| `tube_agent/services/pipeline.py` | shared pipeline (channel → videos → transcripts → embeddings → optional summaries) |
| `tube_agent/services/embeddings.py` | `EmbeddingProvider` ABC, `FastembedProvider` (default), `GeminiEmbeddingProvider` |
| `tube_agent/services/transcripts.py` | yt-dlp caption extractor + segment merger |
| `tube_agent/storage/postgres.py` | SQLAlchemy ORM (SQLite default, Postgres also works) |
| `tube_agent/storage/local.py` | JSON tree fallback for legacy CLI use |
| `tube_agent/api/routes/` | FastAPI endpoints — channels, videos, search, search/semantic, system |
| `tube_agent/api/routes/system.py` | embedding warmup + `/embedding-status` |
| `tube_agent/cli_sidecar.py` | Tauri sidecar entry (`--port`, `--app-data-dir`) |
| `tube_agent/config.py` | `Settings.resolve_app_data_dir()` / `resolve_database_url()` / `resolve_fastembed_cache_dir()` |
| `desktop/src/` | React app (Vite + TanStack Query + React Router + shadcn) |
| `desktop/src-tauri/src/lib.rs` | Rust shell — port allocation, sidecar spawn, process-group cleanup |
| `desktop/scripts/build-sidecar.sh` | PyInstaller bundling for the sidecar |
| `tests/conftest.py` | shared pytest fixtures (in-memory SQLite via StaticPool) |

## Defaults to know

- `DATABASE_URL` empty → derives `sqlite:///{APP_DATA_DIR}/tube_agent.db`
- `APP_DATA_DIR` empty → OS default (`~/Library/Application Support/tube-agent` on macOS)
- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (220 MB, multilingual incl. Korean), downloaded on first run into `{app_data_dir}/fastembed_cache`
- Pipeline: transcripts + embeddings ON, comments + Gemini summaries OFF
- All extra `.env` keys are ignored (`extra="ignore"` in pydantic-settings) — safe to leave stale Supabase/Celery values around

## Conventions

- Reach for the storage/services abstractions; routes shouldn't touch disk or env directly.
- Tests use in-memory SQLite — anything you add to `PostgresStorage` should work without a real Postgres.
- The legacy `Tenant`/`User` schema was removed; if a stale reference shows up in old code, delete rather than restore.
- Keep generated docs and reports in English.
- For desktop changes, prefer `cargo check` over a full `tauri build` while iterating; the release build takes ~3 min on a warm cache.

## Past pivots (so you don't re-debate them)

- Cloud → 100% local: dropped Supabase, Celery, Redis, Cloudflare R2, Fly.io.
- Frontend rebuilt fresh in `desktop/` (Tauri + Vite + React); the Next.js `web/` app was deleted after the Tauri MVP landed.
- Transcripts are the primary feature; Gemini summaries are an opt-in second pass.
- Sidecar uses HTTP on `127.0.0.1:<random-port>` (not Tauri stdio IPC) to keep the FastAPI shape intact.
- Embeddings run on-device via fastembed/ONNX — no API keys required for semantic search.
