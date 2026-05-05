import { useEffect, useMemo, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, RefreshCw } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatNumber } from "@/lib/format";

export function VideoDetailPage() {
  const { handle, videoId } = useParams<{ handle: string; videoId: string }>();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
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

  const summaryQuery = useQuery({
    queryKey: ["summary", videoId],
    queryFn: () => api.videos.getSummary(handle!, videoId!),
    enabled: Boolean(handle && videoId),
    retry: false,
  });

  const summaryMutation = useMutation({
    mutationFn: () => api.videos.generateSummary(handle!, videoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summary", videoId] });
    },
  });

  const transcriptMutation = useMutation({
    mutationFn: () => api.videos.fetchTranscript(handle!, videoId!),
    onSuccess: (data) => {
      queryClient.setQueryData(["transcript", videoId], data);
      queryClient.invalidateQueries({ queryKey: ["transcript", videoId] });
    },
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
  const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}${
    focusSeconds > 0 ? `&t=${Math.floor(focusSeconds)}s` : ""
  }`;

  return (
    <div className="container mx-auto px-6 py-10 max-w-5xl space-y-6">
      {video && (
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight leading-tight">{video.title}</h1>
            <div className="text-xs text-muted-foreground flex flex-wrap gap-4">
              <span>@{handle}</span>
              <span>{formatNumber(video.view_count)} views</span>
              <span>{formatNumber(video.like_count)} likes</span>
              {video.published_at && (
                <span>{new Date(video.published_at).toLocaleDateString()}</span>
              )}
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <a href={youtubeUrl} target="_blank" rel="noreferrer">
              <ExternalLink className="size-4" />
              Open on YouTube
            </a>
          </Button>
        </div>
      )}

      <div className="aspect-video w-full rounded-lg overflow-hidden border bg-black">
        <iframe
          title={video?.title ?? videoId}
          src={embedSrc}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
          className="w-full h-full"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <Tabs defaultValue="summary" className="p-4">
            <div className="flex items-center justify-between gap-4 border-b pb-3">
              <TabsList>
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger value="transcript">Transcript</TabsTrigger>
              </TabsList>
              <span className="text-xs text-muted-foreground">
                {transcriptQuery.isLoading
                  ? "Loading transcript…"
                  : `${segments.length} segments${transcriptQuery.data?.language ? ` · ${transcriptQuery.data.language}` : ""}`}
              </span>
            </div>

            <TabsContent value="summary" className="pt-4 space-y-4">
              {summaryQuery.isLoading && (
                <p className="text-sm text-muted-foreground">Loading summary…</p>
              )}
              {summaryQuery.data ? (
                <div className="space-y-5">
                  {summaryQuery.data.summary_intro && (
                    <p className="text-sm leading-relaxed">{summaryQuery.data.summary_intro}</p>
                  )}
                  {summaryQuery.data.bullets.length > 0 && (
                    <div className="space-y-2">
                      {summaryQuery.data.bullets.map((bullet, i) => (
                        <div key={`${bullet.timestamp}-${i}`} className="rounded-md border px-3 py-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs tabular-nums text-muted-foreground">{bullet.timestamp}</span>
                            <p className="text-sm font-medium">{bullet.title}</p>
                          </div>
                          <p className="mt-1 text-sm text-muted-foreground">{bullet.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {summaryQuery.data.topics.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {summaryQuery.data.topics.map((topic) => (
                        <span key={topic} className="rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
                          {topic}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                !summaryQuery.isLoading && (
                  <div className="rounded-md border border-dashed px-4 py-8 text-center space-y-3">
                    <p className="text-sm text-muted-foreground">
                      {segments.length === 0
                        ? "Capture a transcript before generating a summary."
                        : "No summary has been generated for this video yet."}
                    </p>
                    <div className="flex justify-center gap-2">
                      {segments.length === 0 && (
                        <Button
                          variant="outline"
                          onClick={() => transcriptMutation.mutate()}
                          disabled={transcriptMutation.isPending}
                        >
                          <RefreshCw className={transcriptMutation.isPending ? "size-4 animate-spin" : "size-4"} />
                          {transcriptMutation.isPending ? "Fetching…" : "Fetch transcript"}
                        </Button>
                      )}
                      <Button
                        onClick={() => summaryMutation.mutate()}
                        disabled={summaryMutation.isPending || segments.length === 0}
                      >
                        {summaryMutation.isPending ? "Generating…" : "Generate summary"}
                      </Button>
                    </div>
                    {transcriptMutation.isError && (
                      <p className="text-xs text-destructive">
                        {transcriptMutation.error instanceof Error
                          ? transcriptMutation.error.message
                          : "Transcript fetch failed"}
                      </p>
                    )}
                    {summaryMutation.isError && (
                      <p className="text-xs text-destructive">
                        {summaryMutation.error instanceof Error
                          ? summaryMutation.error.message
                          : "Summary generation failed"}
                      </p>
                    )}
                  </div>
                )
              )}
            </TabsContent>

            <TabsContent value="transcript" className="pt-4">
              <div className="max-h-[480px] overflow-y-auto divide-y rounded-md border">
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
                  <div className="px-4 py-10 text-center text-sm text-muted-foreground space-y-3">
                    <p>No transcript captured for this video.</p>
                    <Button
                      variant="outline"
                      onClick={() => transcriptMutation.mutate()}
                      disabled={transcriptMutation.isPending}
                    >
                      <RefreshCw className={transcriptMutation.isPending ? "size-4 animate-spin" : "size-4"} />
                      {transcriptMutation.isPending ? "Fetching…" : "Fetch transcript"}
                    </Button>
                    {transcriptMutation.isError && (
                      <p className="text-xs text-destructive">
                        {transcriptMutation.error instanceof Error
                          ? transcriptMutation.error.message
                          : "Transcript fetch failed"}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
