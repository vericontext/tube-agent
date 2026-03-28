"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useChannels() {
  return useQuery({
    queryKey: ["channels"],
    queryFn: () => api.channels.list(),
  });
}

export function useChannel(handle: string) {
  return useQuery({
    queryKey: ["channel", handle],
    queryFn: () => api.channels.get(handle),
    enabled: !!handle,
  });
}
