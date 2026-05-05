"""Sidecar entry point for the Tauri desktop app.

Tauri's `Command::new_sidecar(...)` spawns this binary with `--port` and
`--app-data-dir` arguments. Both are forwarded into the FastAPI process via
environment variables so the existing `Settings.resolve_*` helpers pick them
up without any extra wiring.

Built into a single executable via PyInstaller; see
``desktop/scripts/build-sidecar.sh``.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tube-agent-sidecar",
        description="FastAPI sidecar for the Tauri desktop shell",
    )
    parser.add_argument("--port", type=int, default=8000, help="TCP port to bind on 127.0.0.1")
    parser.add_argument(
        "--app-data-dir",
        default="",
        help="OS app data dir (forwarded into APP_DATA_DIR for Settings)",
    )
    args = parser.parse_args()

    if args.app_data_dir:
        os.environ["APP_DATA_DIR"] = args.app_data_dir
        os.environ.setdefault("DATABASE_URL", "")  # force re-derivation

    # Defer import until after env is set so Settings picks up our overrides.
    import uvicorn

    # Tauri sends SIGTERM on app shutdown; uvicorn handles that natively.
    def _stop(*_: object) -> None:
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    uvicorn.run(
        "tube_agent.api.main:app",
        host="127.0.0.1",
        port=args.port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
