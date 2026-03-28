"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useReports(handle: string) {
  return useQuery({
    queryKey: ["reports", handle],
    queryFn: () => api.reports.list(handle),
    enabled: !!handle,
  });
}

export function useReport(handle: string, type: string) {
  return useQuery({
    queryKey: ["report", handle, type],
    queryFn: () => api.reports.get(handle, type),
    enabled: !!handle && !!type,
  });
}
