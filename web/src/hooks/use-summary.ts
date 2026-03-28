"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useSummary(handle: string, videoId: string) {
  return useQuery({
    queryKey: ["summary", handle, videoId],
    queryFn: () => api.videos.getSummary(handle, videoId),
    enabled: !!handle && !!videoId,
  });
}
