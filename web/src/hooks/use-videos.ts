"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useVideo(handle: string, videoId: string) {
  return useQuery({
    queryKey: ["video", handle, videoId],
    queryFn: () => api.videos.get(handle, videoId),
    enabled: !!handle && !!videoId,
  });
}

export function useVideos(
  handle: string,
  opts?: {
    sort_by?: string;
    sort_order?: string;
    offset?: number;
    limit?: number;
  },
) {
  return useQuery({
    queryKey: ["videos", handle, opts],
    queryFn: () => api.videos.list(handle, opts),
    enabled: !!handle,
  });
}
