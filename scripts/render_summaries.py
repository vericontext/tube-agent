"""Render per-video Gemini summaries as readable markdown files."""

from pathlib import Path

from scripts.utils import get_paths, load_json, ensure_dirs_for


def render_summaries(handle: str) -> int:
    """Convert raw summary JSONs to markdown. Returns count of rendered files."""
    paths = get_paths(handle)
    summaries_dir = paths["raw"] / "summaries"
    out_dir = paths["output"] / "summaries"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not summaries_dir.exists():
        print(f"No summaries found at {summaries_dir}")
        return 0

    rendered = 0
    skipped = 0

    for json_path in sorted(summaries_dir.glob("*.json")):
        data = load_json(json_path)
        vid = data.get("videoId", json_path.stem)
        analysis = data.get("analysis")

        md_path = out_dir / f"{vid}.md"
        if md_path.exists():
            skipped += 1
            continue

        if not analysis:
            # Error file or missing analysis
            continue

        md = _render_one(vid, data.get("title", ""), analysis)
        md_path.write_text(md, encoding="utf-8")
        rendered += 1

    print(f"  Rendered: {rendered} new, {skipped} skipped → {out_dir}")
    return rendered


def _render_one(video_id: str, title: str, a: dict) -> str:
    """Render a single summary analysis dict to markdown."""
    lines = []

    # Header
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> YouTube: https://youtube.com/watch?v={video_id}")

    meta_parts = []
    if a.get("content_type"):
        meta_parts.append(f"유형: {a['content_type']}")
    if a.get("tone"):
        meta_parts.append(f"톤: {a['tone']}")
    if a.get("target_audience"):
        meta_parts.append(f"타겟: {a['target_audience']}")
    if meta_parts:
        lines.append(f"> {' | '.join(meta_parts)}")
    lines.append("")

    # Summary intro
    if a.get("summary_intro"):
        lines.append("## 개요")
        lines.append("")
        lines.append(a["summary_intro"])
        lines.append("")

    # Summary bullets
    if a.get("summary_bullets"):
        lines.append("## 핵심 내용")
        lines.append("")
        for b in a["summary_bullets"]:
            ts = b.get("timestamp", "")
            lines.append(f"### {b.get('title', '')} ({ts})")
            lines.append("")
            lines.append(b.get("description", ""))
            lines.append("")

    # Sections
    if a.get("sections"):
        lines.append("## 상세 구간별 내용")
        lines.append("")
        for s in a["sections"]:
            ts = s.get("timestamp", "")
            lines.append(f"### [{ts}] {s.get('title', '')}")
            lines.append("")
            lines.append(s.get("content", ""))
            lines.append("")

    # Topics
    if a.get("topics"):
        lines.append("## 주제 태그")
        lines.append("")
        lines.append(", ".join(f"`{t}`" for t in a["topics"]))
        lines.append("")

    # Mentions
    if a.get("mentions"):
        lines.append("## 언급된 인물/기관")
        lines.append("")
        lines.append(", ".join(a["mentions"]))
        lines.append("")

    # Notable quotes (AI paraphrased)
    if a.get("notable_quotes"):
        lines.append("## Key Statements (AI Paraphrased)")
        lines.append("")
        for q in a["notable_quotes"]:
            lines.append(f"> {q}")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render video summaries to markdown")
    parser.add_argument("handle", help="Channel handle (e.g. eo_korea)")
    args = parser.parse_args()

    handle = args.handle.lstrip("@")
    print(f"Rendering summaries for @{handle}...")
    render_summaries(handle)
