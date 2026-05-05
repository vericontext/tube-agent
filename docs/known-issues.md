# Known Issues

Bookkeeping for bugs / rough edges that are real but not yet fixed. Each
entry is sized so it can be lifted into a GitHub Issue verbatim once the
repo goes public.

---

## 1. First-run indexing skips embeddings if the model is still downloading

**Severity:** medium — first channel index after a fresh install produces
keyword-searchable transcripts but no semantic embeddings until a re-run.

**Reproduce:**
1. `rm -rf ~/Library/Application\ Support/dev.kiyeon.tube-agent` (or fresh install on a new machine).
2. Open the app.
3. Within ~10 s of launch, click *Add channel* → enter a handle → *Start indexing*.
4. Job completes successfully but `progress.embedded_count == 0`.

**Root cause:** `tube_agent/api/main.py` lifespan kicks
`system.start_warmup()` which downloads the fastembed ONNX model
(~220 MB) on a background thread. `tube_agent/api/routes/channels.py::_run_pipeline_job`
calls `get_default_provider()` early in the same window — the model
files don't exist on disk yet, the ONNXRuntime load raises
`NO_SUCHFILE`, the `try/except` in `_run_pipeline_job` catches it and
sets `embedder = None`. Pipeline continues to completion without
embedding.

The pipeline IS idempotent: re-indexing the same channel later (after
warmup completes) skips transcripts but generates the missing embeddings.
Users just hit a confusing "I searched semantically and got nothing"
gap on first run.

**Fix sketch:** in `_run_pipeline_job`, when `body.fetch_transcripts` is
true, poll `system.embedding_status()` for up to ~60 s before invoking
the pipeline so the embedder is ready. Surface this in the Jobs UI as
"Waiting for semantic search index…".

**Files:**
- `tube_agent/api/routes/channels.py` (`_run_pipeline_job`)
- `tube_agent/api/routes/system.py` (`embedding_status`, `_state`)
- `desktop/src/pages/JobPage.tsx` (status messaging)

---

## 2. SidecarGate gives up at 15 s but PyInstaller boot can take 30+ s

**Severity:** medium — the production `.app` shows a false-positive
"Backend did not respond. Retry" on first launch even when everything is
healthy.

**Reproduce:**
1. Build the release `.app` via `bash desktop/scripts/build.sh`.
2. Quit the app and remove `~/Library/Application Support/dev.kiyeon.tube-agent` for a clean state.
3. Open the `.app`.
4. Within ~15 s the splash flips to "Backend did not respond" with a
   Retry button — even though the sidecar comes up shortly after and
   clicking Retry succeeds.

**Root cause:** `desktop/src/components/SidecarGate.tsx` calls
`waitForReady(maxAttempts = 30, intervalMs = 500)` = 15 s total. In
release the sidecar is a PyInstaller `--onefile` binary: bootstrap
extracts itself to a temp dir, exec's a Python interpreter, imports
fastapi/uvicorn/fastembed/etc., binds the port. On a clean machine that
chain commonly takes 30–40 s; on a warm machine it's <5 s.

**Fix sketch:** bump `maxAttempts` to 120 (60 s total) and surface
progressive messaging — "Starting backend… (this can take ~30 s on first
launch)" after the first 5 s. Optionally, have the Rust shell emit a
Tauri event when the sidecar's `/health` first returns 200 and have
`SidecarGate` listen for it instead of (or in addition to) polling.

**Files:**
- `desktop/src/components/SidecarGate.tsx`
- `desktop/src/lib/api.ts` (`waitForReady`)
- `desktop/src-tauri/src/lib.rs` (optional: emit `sidecar://ready` event)

---

## 3. Production `.app` does not load `.env` and ships without API keys

**Severity:** high — first user with no Tube Agent setup history opens
the `.app` and the very first channel index fails with
`Client error '403 Forbidden' ... &key=` because `YOUTUBE_API_KEY` is
empty.

**Reproduce:**
1. `cp -R "Tube Agent.app" /Applications/`
2. Open from `/Applications` (not from the project directory).
3. *Add channel* → ycombinator → fails with 403 from the YouTube API.

**Root cause:** `tube_agent/config.py` `Settings.model_config` has
`env_file=".env"`. `pydantic-settings` resolves that relative to the
process cwd. When launched via Finder / `open -a`, the cwd is `/`, not
the project directory. So no `.env` is loaded; `youtube_api_key` and
`gemini_api_key` default to `""`.

The dev path (`npm run tauri dev`) coincidentally works because the
shell that runs `tauri dev` has cwd at the project root.

**Fix sketches (pick one):**
- **Settings page in the UI (recommended for OSS distribution):** new
  `desktop/src/pages/SettingsPage.tsx` that POSTs the keys to a new
  `/api/v1/system/settings` endpoint; sidecar persists them to
  `{app_data_dir}/secrets.json` and merges into `Settings` at runtime.
  No CLI required, works for non-developer users.
- **Project-aware `.env` lookup:** override `Settings.model_config` to
  also probe `{app_data_dir}/.env` so users can drop a `.env` next to
  the SQLite DB.
- **Rust shell forwards env:** Tauri reads `~/.tube-agent/secrets.env`
  at launch and passes the values via `cmd.env()` when spawning the
  sidecar.

**Files:**
- `tube_agent/config.py` (loader)
- `desktop/src-tauri/src/lib.rs` (env forwarding)
- `desktop/src/pages/SettingsPage.tsx` (new)
- `tube_agent/api/routes/system.py` (`POST /system/settings`)
