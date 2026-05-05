#!/usr/bin/env bash
# Build the FastAPI sidecar into a single binary that Tauri can spawn.
# The output filename includes Rust's target triple so Tauri's sidecar
# resolution picks up the right binary on each platform.
#
# Usage: bash desktop/scripts/build-sidecar.sh
#
# Requires: a Python venv with `pip install -e ".[desktop]"` (provides pyinstaller)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "no Python found at $PY — set PY=/path/to/python" >&2
  exit 1
fi

TARGET_TRIPLE="$(rustc -vV | sed -n 's/host: //p')"
if [ -z "$TARGET_TRIPLE" ]; then
  echo "could not detect rustc host triple" >&2
  exit 1
fi

OUT_DIR="$REPO_ROOT/desktop/src-tauri/binaries"
mkdir -p "$OUT_DIR"

echo ">> building sidecar for $TARGET_TRIPLE..."

"$PY" -m PyInstaller \
  --onefile \
  --noconfirm \
  --name tube-agent-sidecar \
  --paths "$REPO_ROOT" \
  --collect-all fastembed \
  --collect-all onnxruntime \
  --collect-all tokenizers \
  --collect-all huggingface_hub \
  --collect-all google.genai \
  --collect-all yt_dlp \
  --collect-submodules tube_agent \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.http.h11_impl \
  --hidden-import uvicorn.protocols.websockets \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.loops.asyncio \
  --workpath "$REPO_ROOT/build/sidecar-work" \
  --distpath "$REPO_ROOT/build/sidecar-dist" \
  --specpath "$REPO_ROOT/build" \
  "$REPO_ROOT/tube_agent/cli_sidecar.py"

cp "$REPO_ROOT/build/sidecar-dist/tube-agent-sidecar" "$OUT_DIR/tube-agent-sidecar-$TARGET_TRIPLE"
chmod +x "$OUT_DIR/tube-agent-sidecar-$TARGET_TRIPLE"

echo ">> wrote $OUT_DIR/tube-agent-sidecar-$TARGET_TRIPLE"
echo ">> size: $(du -sh "$OUT_DIR/tube-agent-sidecar-$TARGET_TRIPLE" | cut -f1)"
