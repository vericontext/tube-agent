"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ChannelResponse } from "@/lib/types";
import { formatNumber, formatDate } from "@/lib/utils";
import { Users, Video, Eye } from "lucide-react";

export function ChannelCard({ channel }: { channel: ChannelResponse }) {
  return (
    <Link href={`/channels/${channel.handle}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">{channel.title}</CardTitle>
          <p className="text-sm text-muted-foreground">@{channel.handle}</p>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" />
              {formatNumber(channel.subscriber_count)}
            </span>
            <span className="flex items-center gap-1">
              <Video className="h-3.5 w-3.5" />
              {formatNumber(channel.video_count)}
            </span>
            <span className="flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" />
              {formatNumber(channel.view_count)}
            </span>
          </div>
          {channel.country && (
            <Badge variant="secondary" className="mt-3">
              {channel.country}
            </Badge>
          )}
          {channel.fetched_at && (
            <p className="text-xs text-muted-foreground mt-2">
              Analyzed {formatDate(channel.fetched_at)}
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
