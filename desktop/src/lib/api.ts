import { invoke } from "@tauri-apps/api/core";
import type {
  ChannelCreateRequest,
  ChannelListResponse,
  ChannelResponse,
  JobResponse,
  SearchResponse,
  TranscriptResponse,
  VideoListResponse,
  VideoResponse,
} from "./types";

let _baseUrl: string | null = null;

export async function getApiBase(): Promise<string> {
  if (_baseUrl) return _baseUrl;
  const port = await invoke<number>("get_sidecar_port");
  _baseUrl = `http://127.0.0.1:${port}/api/v1`;
  return _baseUrl;
}

async function getRoot(): Promise<string> {
  const base = await getApiBase();
  return base.replace(/\/api\/v1$/, "");
}

export async function pingHealth(): Promise<boolean> {
  try {
    const root = await getRoot();
    const res = await fetch(`${root}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function waitForReady(maxAttempts = 30, intervalMs = 500): Promise<boolean> {
  for (let i = 0; i < maxAttempts; i++) {
    if (await pingHealth()) return true;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const base = await getApiBase();
  const url = new URL(`${base}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new ApiError(res.status, `GET ${path} failed: ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const base = await getApiBase();
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    list: () => get<ChannelListResponse>("/channels"),
    get: (handle: string) => get<ChannelResponse>(`/channels/${handle}`),
    create: (data: ChannelCreateRequest) => post<JobResponse>("/channels", data),
  },
  videos: {
    list: (
      handle: string,
      opts?: { sort_by?: string; sort_order?: string; offset?: number; limit?: number },
    ) =>
      get<VideoListResponse>(`/channels/${handle}/videos`, {
        sort_by: opts?.sort_by ?? "published_at",
        sort_order: opts?.sort_order ?? "desc",
        offset: String(opts?.offset ?? 0),
        limit: String(opts?.limit ?? 50),
      }),
    get: (handle: string, videoId: string) =>
      get<VideoResponse>(`/channels/${handle}/videos/${videoId}`),
    getTranscript: (handle: string, videoId: string, language?: string) =>
      get<TranscriptResponse>(`/channels/${handle}/videos/${videoId}/transcript`, {
        language,
      }),
  },
  jobs: {
    get: (id: string) => get<JobResponse>(`/jobs/${id}`),
  },
  search: {
    keyword: (q: string, type = "all", limit = 20) =>
      get<SearchResponse>("/search", { q, type, limit: String(limit) }),
    semantic: (q: string, channel?: string, limit = 20) =>
      get<SearchResponse>("/search/semantic", {
        q,
        channel,
        limit: String(limit),
      }),
  },
};

export { ApiError };
