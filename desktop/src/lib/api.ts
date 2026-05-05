import { invoke } from "@tauri-apps/api/core";
import type {
  ChannelCreateRequest,
  ChannelListResponse,
  ChannelResponse,
  JobResponse,
  ReportListResponse,
  ReportResponse,
  SearchResponse,
  SettingsStatus,
  SettingsTest,
  SettingsTestResult,
  SettingsUpdate,
  TranscriptResponse,
  VideoSummaryResponse,
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

/**
 * Poll {@link pingHealth} until the sidecar responds or we hit ``maxAttempts``.
 * Default budget is 60 s — release builds extract a PyInstaller --onefile
 * bootstrap and import fastapi/uvicorn/fastembed before binding the port,
 * which routinely takes 30–40 s on a clean machine.
 */
export async function waitForReady(maxAttempts = 120, intervalMs = 500): Promise<boolean> {
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
  if (!res.ok) throw new ApiError(res.status, await responseError("GET", path, res));
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
    throw new ApiError(res.status, await responseError("POST", path, res));
  }
  return res.json();
}

async function responseError(method: string, path: string, res: Response): Promise<string> {
  const text = await res.text().catch(() => "");
  if (text) {
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") return parsed.detail;
    } catch {
      return `${method} ${path} failed: ${text}`;
    }
  }
  return `${method} ${path} failed: ${res.statusText}`;
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
    fetchTranscript: (handle: string, videoId: string) =>
      post<TranscriptResponse>(`/channels/${handle}/videos/${videoId}/transcript`, {
        languages: ["ko", "en"],
        embed: true,
      }),
    getSummary: (handle: string, videoId: string) =>
      get<VideoSummaryResponse>(`/channels/${handle}/videos/${videoId}/summary`),
    generateSummary: (handle: string, videoId: string) =>
      post<VideoSummaryResponse>(`/channels/${handle}/videos/${videoId}/summary`, {
        summary_mode: "transcript",
        summary_language: "en",
      }),
  },
  reports: {
    list: (handle: string) => get<ReportListResponse>(`/channels/${handle}/reports`),
    getOverview: (handle: string) =>
      get<ReportResponse>(`/channels/${handle}/reports/channel_overview`),
    generateOverview: (handle: string) =>
      post<ReportResponse>(`/channels/${handle}/reports/channel_overview`, {}),
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
  system: {
    getSettings: () => get<SettingsStatus>("/system/settings"),
    updateSettings: (body: SettingsUpdate) => post<SettingsStatus>("/system/settings", body),
    testKey: (body: SettingsTest) => post<SettingsTestResult>("/system/settings/test", body),
  },
};

export { ApiError };
