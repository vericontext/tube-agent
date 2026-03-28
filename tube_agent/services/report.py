"""Channel report generation using Gemini."""

import json
from collections import Counter

from tube_agent.storage.base import StorageBackend
from tube_agent.services.gemini import GeminiClient

REPORT_PROMPT = """\
You are a YouTube channel analyst. Based on the data below, write a comprehensive \
channel analysis report in English, in markdown format.

The report must include these sections:

1. **Channel Overview** — subscriber count, total views, video count, founding date, description.
2. **Content Strategy** — main topics, content types, posting frequency/patterns.
3. **Performance Analysis** — top-performing and underperforming videos, engagement rates (like ratio, comment ratio), view distribution.
4. **Trend Analysis** — how topics and performance have evolved over time, monthly upload patterns.
5. **Summary-Based Insights** — key themes and patterns extracted from AI video analyses (summary intros provided).
6. **Recommendations** — actionable suggestions for the channel based on data patterns.

Use concrete numbers and specific video titles. Be analytical, not just descriptive.

Data:
```json
{data}
```

Write the full report in markdown now.
"""


def _prepare_report_data(
    channel: dict,
    videos: list[dict],
    summaries: list[dict],
) -> dict:
    """Aggregate channel data into a structured payload for Gemini."""
    # Sort videos by view count for top/bottom
    sorted_by_views = sorted(
        videos,
        key=lambda v: v.get("viewCount", v.get("view_count", 0)),
        reverse=True,
    )

    def _view_count(v: dict) -> int:
        return v.get("viewCount", v.get("view_count", 0))

    def _like_count(v: dict) -> int:
        return v.get("likeCount", v.get("like_count", 0))

    def _comment_count(v: dict) -> int:
        return v.get("commentCount", v.get("comment_count", 0))

    def _video_brief(v: dict) -> dict:
        return {
            "title": v.get("title", ""),
            "views": _view_count(v),
            "likes": _like_count(v),
            "comments": _comment_count(v),
            "published": v.get("publishedAt", v.get("published_at", "")),
        }

    # Aggregate topics from summaries
    topic_counter = Counter()
    content_types = Counter()
    summary_intros = []
    for s in summaries:
        for topic in (s.get("topics") or []):
            topic_counter[topic] += 1
        ct = s.get("content_type")
        if ct:
            content_types[ct] += 1
        intro = s.get("summary_intro")
        if intro:
            summary_intros.append(intro[:300])

    # Monthly upload counts
    monthly_uploads = Counter()
    for v in videos:
        pub = v.get("publishedAt", v.get("published_at", ""))
        if pub and len(pub) >= 7:
            monthly_uploads[pub[:7]] += 1

    # Engagement averages
    total_views = sum(_view_count(v) for v in videos)
    total_likes = sum(_like_count(v) for v in videos)
    total_comments = sum(_comment_count(v) for v in videos)
    n = len(videos) or 1

    return {
        "channel": {
            "title": channel.get("title", ""),
            "handle": channel.get("handle", ""),
            "subscribers": channel.get("subscriber_count", 0),
            "total_views": channel.get("view_count", 0),
            "video_count": channel.get("video_count", 0),
            "country": channel.get("country", ""),
            "published_at": channel.get("published_at", ""),
            "description": (channel.get("description", "") or "")[:500],
        },
        "top_videos": [_video_brief(v) for v in sorted_by_views[:20]],
        "bottom_videos": [_video_brief(v) for v in sorted_by_views[-5:]],
        "avg_views": total_views // n,
        "avg_likes": total_likes // n,
        "avg_comments": total_comments // n,
        "avg_like_ratio": round(total_likes / total_views, 6) if total_views else 0,
        "avg_comment_ratio": round(total_comments / total_views, 6) if total_views else 0,
        "topic_distribution": dict(topic_counter.most_common(30)),
        "content_type_distribution": dict(content_types.most_common()),
        "monthly_uploads": dict(sorted(monthly_uploads.items())),
        "summary_intros": summary_intros[:30],
        "analyzed_video_count": len(summaries),
        "total_video_count": len(videos),
    }


def generate_channel_report(
    channel_id: str,
    handle: str,
    storage: StorageBackend,
    gemini_client: GeminiClient,
) -> str:
    """Generate comprehensive channel analysis report using Gemini."""
    # 1. Read data from storage
    channel = storage.get_channel(handle)
    if not channel:
        raise ValueError(f"Channel not found: {handle}")

    videos, _ = storage.list_videos(channel_id, sort_by="view_count", limit=200)

    # 2. Collect summaries for analyzed videos
    summaries = []
    for v in videos[:50]:
        vid = v.get("videoId", v.get("video_id"))
        if vid:
            s = storage.get_summary(vid)
            if s:
                summaries.append(s)

    # 3. Aggregate stats
    report_data = _prepare_report_data(channel, videos, summaries)

    # 4. Call Gemini with structured prompt
    prompt = REPORT_PROMPT.format(data=json.dumps(report_data, ensure_ascii=False, default=str))
    print(f"  Sending {len(json.dumps(report_data)):,} chars to Gemini for report generation...")
    content_md = gemini_client.generate_text(prompt)

    # 5. Save via storage backend
    storage.save_report(channel_id, "channel_overview", content_md)
    print(f"  Report generated ({len(content_md):,} chars)")
    return content_md
