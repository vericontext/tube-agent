"""Common utilities for file I/O, formatting, and quota tracking."""

import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "output"


def ensure_dirs():
    """Create all required data directories."""
    for d in [
        DATA_RAW,
        DATA_RAW / "comments",
        DATA_RAW / "summaries",
        DATA_PROCESSED,
        OUTPUT_DIR,
        OUTPUT_DIR / "reports",
    ]:
        d.mkdir(parents=True, exist_ok=True)


def get_paths(handle: str) -> dict:
    """Return channel-specific directory paths."""
    base = BASE_DIR / "data" / handle
    return {
        "raw": base / "raw",
        "processed": base / "processed",
        "output": BASE_DIR / "output" / handle,
    }


def ensure_dirs_for(handle: str):
    """Create all required directories for a specific channel."""
    p = get_paths(handle)
    for d in [
        p["raw"],
        p["raw"] / "comments",
        p["raw"] / "summaries",
        p["processed"],
        p["output"],
        p["output"] / "reports",
    ]:
        d.mkdir(parents=True, exist_ok=True)


def load_json(path: str | Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict | list, path: str | Path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_duration(iso_duration: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or "")
    if not match:
        return 0
    h, m, s = (int(v or 0) for v in match.groups())
    return h * 3600 + m * 60 + s


def format_number(n: int | float) -> str:
    """Format number for display (1.2M, 45K, etc.)."""
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


class QuotaTracker:
    """Track YouTube Data API v3 quota usage."""

    DAILY_LIMIT = 10_000

    def __init__(self):
        self.used = 0
        self.calls = []

    def add(self, method: str, cost: int = 1):
        self.used += cost
        self.calls.append({"method": method, "cost": cost})

    def summary(self) -> str:
        return (
            f"Quota used: {self.used}/{self.DAILY_LIMIT} "
            f"({len(self.calls)} API calls)"
        )
