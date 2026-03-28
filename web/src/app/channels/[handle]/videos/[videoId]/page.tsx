"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSummary } from "@/hooks/use-summary";
import { useChannel } from "@/hooks/use-channels";
import { useVideo, useVideos } from "@/hooks/use-videos";
import { SummaryView } from "@/components/summaries/summary-view";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ExternalLink } from "lucide-react";

export default function VideoSummaryPage({
  params,
}: {
  params: Promise<{ handle: string; videoId: string }>;
}) {
  const { handle, videoId } = use(params);
  const { data: summary, isLoading } = useSummary(handle, videoId);
  const { data: channel } = useChannel(handle);
  const { data: videoDetail } = useVideo(handle, videoId);
  const { data: videoList } = useVideos(handle);
  const video = videoDetail ?? videoList?.videos.find((v) => v.video_id === videoId);

  // Resizable panels
  const [leftPercent, setLeftPercent] = useState(55);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setLeftPercent(Math.min(70, Math.max(30, pct)));
    };
    const onMouseUp = () => {
      setIsDragging(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDragging]);

  return (
    <div className="max-w-7xl mx-auto space-y-4">
      <Button variant="ghost" size="sm" nativeButton={false} render={<Link href={`/channels/${handle}`} />}>
        <ChevronLeft className="h-4 w-4 mr-1" />
        Back to channel
      </Button>

      {/* Mobile: stack / Desktop: resizable 2-col */}
      <div ref={containerRef} className="lg:flex">
        {/* Left: Video player */}
        <div
          className="lg:shrink-0 lg:sticky lg:top-20 lg:self-start space-y-3"
          style={{ flexBasis: `${leftPercent}%` }}
        >
          <div className="aspect-video w-full relative">
            <iframe
              className="w-full h-full rounded-lg"
              src={`https://www.youtube.com/embed/${videoId}`}
              title="YouTube video"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
            {isDragging && (
              <div className="absolute inset-0" />
            )}
          </div>

          {/* Video title + channel */}
          {video && (
            <div className="space-y-1">
              <h1 className="text-lg font-semibold leading-tight">{video.title}</h1>
              {channel && (
                <p className="text-sm text-muted-foreground">{channel.title}</p>
              )}
            </div>
          )}

          {/* Attribution */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <p>
              Content from YouTube. All rights belong to the original creator.
            </p>
            <a
              href={`https://www.youtube.com/watch?v=${videoId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-foreground transition-colors"
            >
              Watch on YouTube
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>

        {/* Drag handle — desktop only */}
        <div
          className="hidden lg:flex items-center justify-center w-4 shrink-0 cursor-col-resize group"
          onMouseDown={onMouseDown}
        >
          <div className="w-1 h-12 rounded-full bg-border group-hover:bg-primary/40 transition-colors" />
        </div>

        {/* Right: Summary */}
        <div className="lg:min-w-0 lg:flex-1 mt-6 lg:mt-0">
          <SummaryView summary={summary} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
