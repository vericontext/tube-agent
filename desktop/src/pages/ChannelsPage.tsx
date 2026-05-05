import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { AddChannelDialog } from "@/components/AddChannelDialog";
import { Card, CardContent } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";

export function ChannelsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["channels"],
    queryFn: () => api.channels.list(),
    refetchInterval: 5_000,
  });

  return (
    <div className="container mx-auto px-6 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Channels</h1>
        <AddChannelDialog />
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading channels…</p>}
      {isError && <p className="text-sm text-destructive">Could not reach the backend.</p>}

      {data && data.channels.length === 0 && (
        <Card className="bg-muted/30">
          <CardContent className="p-10 text-center text-sm text-muted-foreground">
            No channels yet. Add one to start indexing transcripts.
          </CardContent>
        </Card>
      )}

      {data && data.channels.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.channels.map((ch) => (
            <Link to={`/channels/${ch.handle}`} key={ch.id}>
              <Card className="transition hover:border-foreground/40 h-full">
                <CardContent className="p-5 space-y-3">
                  <div>
                    <h2 className="font-semibold leading-tight">{ch.title}</h2>
                    <p className="text-xs text-muted-foreground">@{ch.handle}</p>
                  </div>
                  <div className="text-xs text-muted-foreground flex gap-4">
                    <span>{formatNumber(ch.subscriber_count)} subs</span>
                    <span>{ch.video_count.toLocaleString()} videos</span>
                    <span>{formatNumber(ch.view_count)} views</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
