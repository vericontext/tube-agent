"use client";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { TranscriptResponse } from "@/lib/types";

export function TranscriptView({
  transcript,
  isLoading,
}: {
  transcript?: TranscriptResponse;
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (!transcript || transcript.segments.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        No transcript available for this video.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {transcript.language && (
          <Badge variant="secondary">{transcript.language}</Badge>
        )}
        <span className="text-sm text-muted-foreground">
          {transcript.segments.length} timestamped segments
        </span>
      </div>

      <div className="divide-y rounded-lg border">
        {transcript.segments.map((segment, i) => (
          <div key={`${segment.start_seconds}-${i}`} className="flex gap-3 px-4 py-3">
            <a
              href={`https://www.youtube.com/watch?v=${segment.video_id}&t=${Math.floor(segment.start_seconds)}s`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-primary shrink-0 pt-1"
            >
              {segment.timestamp}
            </a>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {segment.text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
