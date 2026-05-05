# Changelog

All notable user-facing, release, and packaging changes are tracked here.

This project follows a SemVer-like `0.y.z` policy while the app is pre-1.0:

- Patch: fixes, docs, release automation, packaging improvements.
- Minor: new user-facing capabilities or meaningful workflow changes.
- Major: reserved until the app reaches `1.0.0`.

Every release tag must match the desktop app version and have a matching
`CHANGELOG.md` entry.

## [Unreleased]

## [0.0.2] - 2026-05-06

### Added

- Transcript-backed English video summaries generated from saved transcript segments.
- Channel overview generation from saved video summaries.
- Desktop UI for summary generation, summary viewing, and channel overview viewing.
- GitHub Actions CI for Python tests, frontend build, and macOS Apple Silicon package smoke builds.
- Tag-triggered GitHub Actions release workflow that creates an unsigned Apple Silicon draft release.
- CI-success auto-tag workflow that drafts a release when `main` has a new desktop version.
- Desktop version consistency check for `package.json`, `tauri.conf.json`, and `Cargo.toml`.
- Release guide with version bump, changelog, and unsigned macOS install rules.

### Changed

- Default desktop summary flow now uses transcript text and summarizes the latest 10 videos when enabled.
- Channel overview prompt is viewer-focused rather than channel-operator-focused.
- Desktop Rust package metadata now matches the `0.0.2` app version.

## [0.0.1] - 2026-05-05

### Added

- First public Apple Silicon macOS preview release.
- Local-first Tauri desktop shell with FastAPI sidecar.
- YouTube channel and video metadata indexing.
- Transcript extraction via yt-dlp.
- On-device multilingual embeddings through fastembed/ONNX.
- Keyword and semantic transcript search.
- Video detail view with embedded YouTube player and transcript navigation.
- In-app Settings for local YouTube and Gemini API key storage.
