# Tube Agent — Desktop

Tauri 2 + Vite + React 19 + Tailwind 4 shell that wraps the Python core (FastAPI sidecar with yt-dlp, Gemini, fastembed) into a single double-click app.

v0.0.2 adds transcript-backed English summaries for the latest videos and a channel overview generated from saved summaries. v0.0.1 was primarily a transcript indexing + search preview.

```
desktop/
├── src/                React UI (TanStack Query, React Router, shadcn)
├── src-tauri/          Rust shell — spawns the Python sidecar, exposes its port to the webview
│   ├── binaries/       PyInstaller-built sidecar (one binary per target triple)
│   ├── icons/          App icons (regenerate via `npx tauri icon <source>.png`)
│   └── tauri.conf.json
├── scripts/
│   ├── build-sidecar.sh   PyInstaller → single-file binary
│   └── build.sh           Full release: sidecar + tauri bundle
└── package.json
```

## Architecture

```
┌────────── Tauri (Rust) ──────────┐
│                                  │
│   WebView (React app)            │   ──invoke('get_sidecar_port')──┐
│       ↓ fetch                                                       │
│   http://127.0.0.1:<port>/...    │   ←─ on app launch:              │
│                                  │      1. pick free port           │
│   Spawned child process:         │      2. spawn sidecar w/ port    │
│     tube-agent-sidecar           │   ←─ on quit:  child.kill()      │
│       (FastAPI + uvicorn)        │                                  │
└──────────────────────────────────┘
```

- **Dev** (`npm run tauri dev`): the Rust shell spawns `python -m tube_agent.cli_sidecar` from the project venv. No PyInstaller needed.
- **Release** (`bash desktop/scripts/build.sh`): PyInstaller bundles the sidecar into a single binary, Tauri's `bundle.externalBin` ships it inside the `.app`.

## Develop

```bash
# from the repo root
python -m venv .venv
.venv/bin/pip install -e ".[dev,desktop]"

cd desktop
npm install
npm run tauri dev
```

The first `cargo build` takes ~3 min on a clean machine. The sidecar's first run downloads the embedding model (~220 MB) into the OS app data dir; subsequent launches reuse the cache.

App data lives at:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/dev.kiyeon.tube-agent/` |
| Linux | `~/.local/share/dev.kiyeon.tube-agent/` |
| Windows | `%APPDATA%\dev.kiyeon.tube-agent\` |

To wipe state and start fresh, `rm -rf` that directory.

## Release build (macOS)

```bash
bash desktop/scripts/build.sh
```

This:
1. Detects the host triple via `rustc -vV`.
2. Runs `pyinstaller` against `tube_agent/cli_sidecar.py` with the necessary `--collect-all` flags for `fastembed`, `onnxruntime`, `tokenizers`, `huggingface_hub`, `google.genai`, and `yt_dlp`.
3. Copies the result to `desktop/src-tauri/binaries/tube-agent-sidecar-<triple>` (Tauri's required naming).
4. Runs `npm run tauri build`.

The resulting `.app` and `.dmg` end up under `desktop/src-tauri/target/release/bundle/`. Expect ~250–350 MB of ONNX runtime + embedded Python.

### Code signing (macOS)

Without signing, Gatekeeper blocks the app on other Macs. To sign + notarize:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_ID="you@example.com"
export APPLE_PASSWORD="app-specific-password"
export APPLE_TEAM_ID="TEAMID"

bash desktop/scripts/build.sh
```

Tauri picks up these env vars via `bundle.macOS.signingIdentity`. Notarization is automatic when `APPLE_ID` / `APPLE_PASSWORD` / `APPLE_TEAM_ID` are set.

For local dev / personal use without an Apple Developer membership, ad-hoc signing works:

```bash
codesign --force --deep --sign - desktop/src-tauri/target/release/bundle/macos/Tube\ Agent.app
```

### Windows / Linux

Cross-compiling is out of scope — build from a host of the target OS. The `build-sidecar.sh` script auto-detects the local triple, so on Linux/Windows it produces `tube-agent-sidecar-<linux/windows-triple>` next to `tauri.conf.json`'s `bundle.externalBin` entry.

## Notes / known limitations

- `bundle.externalBin` requires an *exact* file at `binaries/tube-agent-sidecar-<host-triple>` at build time. If `tauri build` fails with "external binary not found", run `bash desktop/scripts/build-sidecar.sh` first.
- The embedding model is downloaded on first run from Hugging Face Hub. Offline-first installs would need to pre-bake the model into the bundle (defer).
- Gemini summaries require a Gemini API key in Settings. Search and transcript indexing still work without it.
- The default summary path uses saved transcript text, not multimodal video analysis. The older multimodal path remains available from the CLI/API for experimentation.
- Intel Mac builds still need to be produced on an x86_64 macOS host or GitHub Actions runner.
