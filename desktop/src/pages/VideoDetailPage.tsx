import { useEffect, useMemo, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";

export function VideoDetailPage() {
  const { handle, videoId } = useParams<{ handle: string; videoId: string }>();
  const [searchParams] = useSearchParams();
  const focusSeconds = Number.parseInt(searchParams.get("t") ?? "0", 10) || 0;

  const videoQuery = useQuery({
    queryKey: ["video", videoId],
    queryFn: () => api.videos.get(handle!, videoId!),
    enabled: Boolean(handle && videoId),
  });

  const transcriptQuery = useQuery({
    queryKey: ["transcript", videoId],
    queryFn: () => api.videos.getTranscript(handle!, videoId!),
    enabled: Boolean(handle && videoId),
  });

  const segments = transcriptQuery.data?.segments ?? [];

  const focusIndex = useMemo(() => {
    if (!focusSeconds || segments.length === 0) return -1;
    let lastBefore = -1;
    for (let i = 0; i < segments.length; i++) {
      if (segments[i].start_seconds <= focusSeconds) lastBefore = i;
      else break;
    }
    return lastBefore;
  }, [focusSeconds, segments]);

  const segmentRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (focusIndex < 0) return;
    const el = segmentRefs.current[focusIndex];
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusIndex, segments.length]);

  const embedSrc = videoId
    ? `https://www.youtube.com/embed/${videoId}?start=${Math.max(0, Math.floor(focusSeconds))}&autoplay=${focusSeconds > 0 ? 1 : 0}`
    : "";

  if (!handle || !videoId) return null;

  const video = videoQuery.data;

  return (
    <div className="container mx-auto px-6 py-10 max-w-5xl space-y-6">
      {video && (
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight leading-tight">{video.title}</h1>
          <div className="text-xs text-muted-foreground flex gap-4">
            <span>@{handle}</span>
            <span>{formatNumber(video.view_count)} views</span>
            <span>{formatNumber(video.like_count)} likes</span>
            {video.published_at && (
              <span>{new Date(video.published_at).toLocaleDateString()}</span>
            )}
          </div>
        </div>
      )}

      <div className="aspect-video w-full rounded-lg overflow-hidden border bg-black">
        <iframe
          title={video?.title ?? videoId}
          src={embedSrc}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="w-full h-full"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="px-4 py-3 border-b text-xs text-muted-foreground flex items-center justify-between">
            <span>Transcript</span>
            <span>
              {transcriptQuery.isLoading
                ? "Loading…"
                : `${segments.length} segments${transcriptQuery.data?.language ? ` · ${transcriptQuery.data.language}` : ""}`}
            </span>
          </div>
          <div className="max-h-[480px] overflow-y-auto divide-y">
            {segments.map((seg, i) => {
              const isFocus = i === focusIndex;
              return (
                <div
                  key={`${seg.start_seconds}-${i}`}
                  ref={(el) => {
                    segmentRefs.current[i] = el;
                  }}
                  className={
                    "px-4 py-2 grid grid-cols-[60px_1fr] gap-3 text-sm transition " +
                    (isFocus ? "bg-emerald-500/10" : "hover:bg-muted/50")
                  }
                >
                  <a
                    href={`https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seg.start_seconds)}s`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs tabular-nums text-muted-foreground hover:underline"
                  >
                    {seg.timestamp}
                  </a>
                  <p className="leading-snug">{seg.text}</p>
                </div>
              );
            })}
            {segments.length === 0 && !transcriptQuery.isLoading && (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                No transcript captured for this video.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
