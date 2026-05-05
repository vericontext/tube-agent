"use client";

import { useChannels } from "@/hooks/use-channels";
import { ChannelCard } from "@/components/channels/channel-card";
import { AddChannelDialog } from "@/components/channels/add-channel-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Activity } from "lucide-react";

export default function DashboardPage() {
  const { data, isLoading } = useChannels();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Channels</h1>
        <AddChannelDialog />
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && data?.channels.length === 0 && (
        <div className="text-center py-20">
          <Activity className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-lg font-semibold mb-2">No channels yet</h2>
          <p className="text-muted-foreground mb-4">
            Add a YouTube channel to start indexing transcripts
          </p>
          <AddChannelDialog />
        </div>
      )}

      {data && data.channels.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.channels.map((channel) => (
            <ChannelCard key={channel.id} channel={channel} />
          ))}
        </div>
      )}
    </div>
  );
}
