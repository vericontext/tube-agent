import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration, formatNumber } from "@/lib/format";

export function ChannelDetailPage() {
  const { handle } = useParams<{ handle: string }>();
  const queryClient = useQueryClient();

  const channelQuery = useQuery({
    queryKey: ["channel", handle],
    queryFn: () => api.channels.get(handle!),
    enabled: Boolean(handle),
  });

  const videosQuery = useQuery({
    queryKey: ["videos", handle],
    queryFn: () => api.videos.list(handle!, { sort_by: "published_at", sort_order: "desc", limit: 100 }),
    enabled: Boolean(handle),
  });

  const overviewQuery = useQuery({
    queryKey: ["channel-overview", handle],
    queryFn: () => api.reports.getOverview(handle!),
    enabled: Boolean(handle),
    retry: false,
  });

  const overviewMutation = useMutation({
    mutationFn: () => api.reports.generateOverview(handle!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channel-overview", handle] });
    },
  });

  if (!handle) return null;

  const channel = channelQuery.data;
  const videos = videosQuery.data?.videos ?? [];

  return (
    <div className="container mx-auto px-6 py-10 space-y-8">
      {channelQuery.isLoading && <p className="text-sm text-muted-foreground">Loading channel…</p>}
      {channelQuery.isError && <p className="text-sm text-destructive">Channel not found.</p>}
      {channel && (
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">{channel.title}</h1>
          <p className="text-xs text-muted-foreground">@{channel.handle}</p>
          <div className="text-xs text-muted-foreground flex gap-4">
            <span>{formatNumber(channel.subscriber_count)} subs</span>
            <span>{channel.video_count.toLocaleString()} total videos</span>
            <span>{formatNumber(channel.view_count)} views</span>
          </div>
        </div>
      )}

      <Card>
        <CardContent className="p-4 space-y-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold">Channel overview</h2>
              <p className="text-xs text-muted-foreground">
                Generated from saved video summaries.
              </p>
            </div>
            {!overviewQuery.data && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => overviewMutation.mutate()}
                disabled={overviewMutation.isPending}
              >
                {overviewMutation.isPending ? "Generating…" : "Generate overview"}
              </Button>
            )}
          </div>
          {overviewQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading overview…</p>
          )}
          {overviewQuery.data ? (
            <div className="max-w-none whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
              {overviewQuery.data.content_md}
            </div>
          ) : (
            !overviewQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                No channel overview yet. Generate summaries for videos first, then create an overview.
              </p>
            )
          )}
          {overviewMutation.isError && (
            <p className="text-xs text-destructive">
              {overviewMutation.error instanceof Error
                ? overviewMutation.error.message
                : "Overview generation failed"}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase text-muted-foreground border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Title</th>
                <th className="text-right px-4 py-3 font-medium">Views</th>
                <th className="text-right px-4 py-3 font-medium">Likes</th>
                <th className="text-right px-4 py-3 font-medium">Duration</th>
                <th className="text-right px-4 py-3 font-medium">Published</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((v) => (
                <tr key={v.video_id} className="border-b last:border-0 hover:bg-muted/40">
                  <td className="px-4 py-2">
                    <Link to={`/channels/${handle}/videos/${v.video_id}`} className="hover:underline">
                      {v.title}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">{formatNumber(v.view_count)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{formatNumber(v.like_count)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{formatDuration(v.duration_seconds)}</td>
                  <td className="px-4 py-2 text-right text-muted-foreground">
                    {v.published_at ? new Date(v.published_at).toLocaleDateString() : ""}
                  </td>
                </tr>
              ))}
              {videos.length === 0 && !videosQuery.isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-muted-foreground text-sm">
                    No videos indexed yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
