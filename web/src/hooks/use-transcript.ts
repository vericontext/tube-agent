"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useTranscript(handle: string, videoId: string, language?: string) {
  return useQuery({
    queryKey: ["transcript", handle, videoId, language],
    queryFn: () => api.videos.getTranscript(handle, videoId, language),
    enabled: !!handle && !!videoId,
  });
}
