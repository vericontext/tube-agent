"""Check that desktop release metadata agrees.

The desktop app version is duplicated across Node, Tauri, and Cargo files.
Release automation uses this check to prevent publishing a tag whose artifact
metadata points at a different version.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _desktop_versions() -> dict[str, str]:
    return {
        "desktop/package.json": _read_json(ROOT / "desktop/package.json")["version"],
        "desktop/src-tauri/tauri.conf.json": _read_json(
            ROOT / "desktop/src-tauri/tauri.conf.json"
        )["version"],
        "desktop/src-tauri/Cargo.toml": _read_toml(ROOT / "desktop/src-tauri/Cargo.toml")[
            "package"
        ]["version"],
    }


def main() -> int:
    print_only = "--print" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--print"]
    expected = args[0].removeprefix("v") if args else None

    versions = _desktop_versions()

    unique_versions = set(versions.values())
    errors: list[str] = []
    if len(unique_versions) != 1:
        errors.append("desktop version files disagree:")
        errors.extend(f"  {path}: {version}" for path, version in versions.items())

    actual = next(iter(unique_versions))
    if expected and actual != expected:
        errors.append(f"tag version mismatch: tag={expected}, desktop={actual}")

    if expected:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        if f"## [{expected}]" not in changelog:
            errors.append(f"missing CHANGELOG.md entry: ## [{expected}]")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(actual if print_only else f"desktop version ok: {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
