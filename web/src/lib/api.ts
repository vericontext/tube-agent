import type {
  ChannelListResponse,
  ChannelResponse,
  ChannelCreateRequest,
  VideoListResponse,
  VideoResponse,
  VideoSummaryResponse,
  JobResponse,
  ReportListResponse,
  ReportResponse,
  SearchResponse,
} from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://tube-agent-api.fly.dev/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiGet<T>(
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const url = new URL(`${API_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed: ${res.statusText}`);
  }
  return res.json();
}

async function apiPost<T>(
  path: string,
  body: unknown,
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, `POST ${path} failed: ${text}`);
  }
  return res.json();
}

export const api = {
  channels: {
    list: (offset = 0, limit = 50) =>
      apiGet<ChannelListResponse>("/channels", {
        offset: String(offset),
        limit: String(limit),
      }),
    get: (handle: string) => apiGet<ChannelResponse>(`/channels/${handle}`),
    create: (data: ChannelCreateRequest, token: string) =>
      apiPost<JobResponse>("/channels", data, token),
  },
  videos: {
    list: (
      handle: string,
      opts?: {
        sort_by?: string;
        sort_order?: string;
        offset?: number;
        limit?: number;
      },
    ) =>
      apiGet<VideoListResponse>(`/channels/${handle}/videos`, {
        sort_by: opts?.sort_by || "published_at",
        sort_order: opts?.sort_order || "desc",
        offset: String(opts?.offset ?? 0),
        limit: String(opts?.limit ?? 50),
      }),
    get: (handle: string, videoId: string) =>
      apiGet<VideoResponse>(`/channels/${handle}/videos/${videoId}`),
    getSummary: (handle: string, videoId: string) =>
      apiGet<VideoSummaryResponse>(
        `/channels/${handle}/videos/${videoId}/summary`,
      ),
  },
  reports: {
    list: (handle: string) =>
      apiGet<ReportListResponse>(`/channels/${handle}/reports`),
    get: (handle: string, type: string) =>
      apiGet<ReportResponse>(`/channels/${handle}/reports/${type}`),
  },
  search: {
    query: (q: string, type = "all", limit = 20) =>
      apiGet<SearchResponse>("/search", {
        q,
        type,
        limit: String(limit),
      }),
  },
  jobs: {
    get: (id: string) => apiGet<JobResponse>(`/jobs/${id}`),
  },
};
