#!/usr/bin/env bash
# End-to-end desktop build: PyInstaller sidecar + Tauri bundle.
# Output goes to desktop/src-tauri/target/release/bundle/.
#
# Usage:  bash desktop/scripts/build.sh
#
# Prerequisites:
#   - Python venv at .venv with `pip install -e ".[desktop]"`
#   - npm deps installed in desktop/  (`npm install`)
#   - Rust toolchain installed
#   - macOS signing: APPLE_SIGNING_IDENTITY env var, plus APPLE_ID,
#     APPLE_PASSWORD, APPLE_TEAM_ID for notarization (see README).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Building Python sidecar"
bash "$SCRIPT_DIR/build-sidecar.sh"

echo
echo "==> Building Tauri bundle"
cd "$DESKTOP_DIR"
npm run tauri build

echo
echo "==> Done. Bundle artifacts:"
find "$DESKTOP_DIR/src-tauri/target/release/bundle" -maxdepth 3 -type f \( -name "*.dmg" -o -name "*.app" -o -name "*.msi" -o -name "*.AppImage" -o -name "*.deb" \) 2>/dev/null || true
