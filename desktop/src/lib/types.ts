// Mirrors the FastAPI Pydantic schemas in tube_agent/models/schemas.py.

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface ChannelResponse {
  id: string;
  handle: string;
  title: string;
  description: string;
  country: string;
  subscriber_count: number;
  view_count: number;
  video_count: number;
  published_at: string | null;
  fetched_at: string | null;
  updated_at: string | null;
}

export interface ChannelListResponse {
  channels: ChannelResponse[];
  total: number;
}

export interface VideoResponse {
  video_id: string;
  channel_id: string;
  title: string;
  description: string;
  published_at: string | null;
  tags: string[];
  category_id: string;
  duration_seconds: number;
  view_count: number;
  like_count: number;
  comment_count: number;
  like_ratio: number;
  comment_ratio: number;
  fetched_at: string | null;
  has_summary: boolean;
}

export interface VideoListResponse {
  videos: VideoResponse[];
  total: number;
}

export interface TranscriptSegmentResponse {
  video_id: string;
  language: string;
  source: string;
  start_seconds: number;
  end_seconds: number;
  timestamp: string;
  text: string;
}

export interface TranscriptResponse {
  video_id: string;
  language: string | null;
  segments: TranscriptSegmentResponse[];
}

export interface SummarySectionResponse {
  timestamp: string;
  title: string;
  content: string;
}

export interface SummaryBulletResponse {
  title: string;
  timestamp: string;
  description: string;
}

export interface VideoSummaryResponse {
  video_id: string;
  summary_intro: string | null;
  topics: string[];
  content_type: string | null;
  target_audience: string | null;
  tone: string | null;
  mentions: string[];
  notable_quotes: string[];
  sections: SummarySectionResponse[];
  bullets: SummaryBulletResponse[];
  created_at: string | null;
}

export interface ReportResponse {
  id: number;
  channel_id: string;
  report_type: string;
  content_md: string;
  created_at: string | null;
}

export interface ReportListResponse {
  reports: ReportResponse[];
  total: number;
}

export interface JobResponse {
  id: string;
  channel_id: string | null;
  job_type: string;
  status: JobStatus;
  progress: Record<string, unknown>;
  config: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface SearchResult {
  type: "video" | "summary" | "transcript";
  video_id: string;
  title: string;
  snippet: string;
  score: number;
  channel_handle: string | null;
  video_title: string | null;
  start_seconds: number | null;
  timestamp: string | null;
  youtube_url: string | null;
  language: string | null;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export interface ChannelCreateRequest {
  handle: string;
  max_videos?: number;
  skip_comments?: boolean;
  skip_summaries?: boolean;
  summary_max?: number | null;
  media_resolution?: string;
  summary_mode?: string;
  summary_language?: string;
  fetch_transcripts?: boolean;
  transcript_languages?: string[];
}

export interface SettingsStatus {
  youtube_api_key: "set" | "unset";
  gemini_api_key: "set" | "unset";
  app_data_dir: string;
}

export interface SettingsUpdate {
  youtube_api_key?: string;
  gemini_api_key?: string;
}

export interface SettingsTest {
  provider: "youtube" | "gemini";
  api_key: string;
}

export interface SettingsTestResult {
  ok: boolean;
  error: string | null;
}
