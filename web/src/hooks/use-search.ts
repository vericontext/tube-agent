"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useSearch(query: string, type = "all") {
  return useQuery({
    queryKey: ["search", query, type],
    queryFn: () => api.search.query(query, type),
    enabled: query.length > 0,
  });
}
