"use client";

import { use } from "react";
import { useChannel } from "@/hooks/use-channels";
import { useReports } from "@/hooks/use-reports";
import { VideoTable } from "@/components/videos/video-table";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber, formatDate } from "@/lib/utils";
import { Users, Eye, Video, Globe, Info } from "lucide-react";
import Link from "next/link";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <Icon className="h-5 w-5 text-muted-foreground" />
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ChannelPage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = use(params);
  const { data: channel, isLoading } = useChannel(handle);
  const { data: reportsData } = useReports(handle);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!channel) {
    return <p className="text-center py-12 text-muted-foreground">Channel not found.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold">{channel.title}</h1>
            <p className="text-muted-foreground">@{channel.handle}</p>
          </div>
          <a
            href={`https://www.youtube.com/@${channel.handle}`}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            View on YouTube
          </a>
        </div>
        {channel.fetched_at && (
          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
            <Info className="h-3 w-3" />
            Data collected on {formatDate(channel.fetched_at)}. Statistics may differ from current values.
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label="Subscribers"
          value={formatNumber(channel.subscriber_count)}
        />
        <StatCard
          icon={Eye}
          label="Total Views"
          value={formatNumber(channel.view_count)}
        />
        <StatCard
          icon={Video}
          label="Videos"
          value={formatNumber(channel.video_count)}
        />
        <StatCard
          icon={Globe}
          label="Country"
          value={channel.country || "—"}
        />
      </div>

      <Tabs defaultValue="videos">
        <TabsList>
          <TabsTrigger value="videos">Videos</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>

        <TabsContent value="videos" className="mt-4">
          <VideoTable handle={handle} />
        </TabsContent>

        <TabsContent value="reports" className="mt-4">
          {reportsData && reportsData.reports.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {reportsData.reports.map((report) => (
                <Link
                  key={report.id}
                  href={`/channels/${handle}/reports/${report.report_type}`}
                >
                  <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                    <CardContent className="p-4">
                      <Badge variant="secondary" className="mb-2">
                        {report.report_type.replace(/_/g, " ")}
                      </Badge>
                      <p className="text-sm text-muted-foreground">
                        Created {formatDate(report.created_at)}
                      </p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-muted-foreground">
              No reports available yet.
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
