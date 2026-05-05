# Tube Agent Release Process

Tube Agent releases are built by GitHub Actions from a clean checkout. Local builds
are useful for smoke tests, but the downloadable artifact should come from the
tagged release workflow.

## Current Policy

- Trigger: push a Git tag named `v0.0.x`.
- Artifact: unsigned macOS Apple Silicon DMG.
- Release state: GitHub draft release until a human smoke-tests the DMG.
- API keys: never baked into the app; users enter YouTube and Gemini keys in Settings.
- Changelog: every release must have a matching `CHANGELOG.md` entry.

## Version Bump Rules

Tube Agent uses a SemVer-like `0.y.z` policy while it is pre-1.0:

- Patch (`0.0.x`): fixes, docs, release automation, packaging improvements.
- Minor (`0.x.0`): new user-facing capabilities or meaningful workflow changes.
- Major (`1.0.0+`): only after the app is ready for a stable public contract.

For desktop releases, bump these files together:

```text
desktop/package.json
desktop/src-tauri/tauri.conf.json
desktop/src-tauri/Cargo.toml
```

Do not use `pyproject.toml` as the desktop release source of truth. It is Python
package metadata and can move on a separate cadence.

Agents must update `CHANGELOG.md` in the same PR/commit as any release-worthy
change. Add unreleased work under `[Unreleased]`; when cutting a release, move
those notes under the matching version heading.

## Release Checklist

1. Update the desktop version in all three files:

   ```text
   desktop/package.json
   desktop/src-tauri/tauri.conf.json
   desktop/src-tauri/Cargo.toml
   ```

2. Move relevant changelog entries from `[Unreleased]` into the new version heading:

   ```text
   ## [0.0.2] - 2026-05-06
   ```

3. Run local checks:

   ```bash
   .venv/bin/python scripts/check_desktop_version.py
   .venv/bin/pytest tests/ -q
   cd desktop && npm run build
   git diff --check
   ```

4. Commit and push to `main`.

5. Confirm the `CI` workflow is green on `main`.

6. Create and push the release tag:

   ```bash
   git tag v0.0.2
   git push origin v0.0.2
   ```

7. Wait for the `Release` workflow to create a draft GitHub Release.

8. Download the DMG from the draft release and smoke-test it on Apple Silicon macOS:

   - Open the DMG.
   - Drag Tube Agent to Applications.
   - Launch the app.
   - Confirm the Channels screen loads.
   - Open Settings and confirm YouTube/Gemini key status is shown.
   - Add a small channel or use existing local data to confirm the sidecar starts.

9. Edit the draft release notes with:

   - What changed.
   - What works.
   - Known limitations.
   - Unsigned install instructions below.

10. Publish the draft release.

## Unsigned macOS Install

Until Apple Developer signing and notarization are configured, macOS Gatekeeper
will block the app on first launch. After dragging the app to Applications, run:

```bash
xattr -dr com.apple.quarantine /Applications/Tube\ Agent.app
```

Then launch Tube Agent from Applications or Spotlight.

## Future Signing Upgrade

To remove the Gatekeeper workaround, add Apple Developer signing and
notarization to the release workflow. Required GitHub secrets will include an
exported Developer ID Application certificate plus Apple notarization
credentials. Keep this separate from the unsigned release workflow until the
certificate setup is verified.
