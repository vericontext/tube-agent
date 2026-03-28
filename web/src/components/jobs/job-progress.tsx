"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { JobResponse } from "@/lib/types";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

const STATUS_CONFIG = {
  pending: { icon: Clock, label: "Pending", variant: "secondary" as const },
  running: { icon: Loader2, label: "Running", variant: "default" as const },
  completed: { icon: CheckCircle2, label: "Completed", variant: "secondary" as const },
  failed: { icon: XCircle, label: "Failed", variant: "destructive" as const },
};

export function JobProgress({
  job,
  isLoading,
}: {
  job?: JobResponse;
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-4 text-center py-12">
        <Skeleton className="h-12 w-12 rounded-full mx-auto" />
        <Skeleton className="h-6 w-48 mx-auto" />
        <Skeleton className="h-4 w-64 mx-auto" />
      </div>
    );
  }

  if (!job) return null;

  const config = STATUS_CONFIG[job.status];
  const Icon = config.icon;
  const isRunning = job.status === "running" || job.status === "pending";
  const progress = job.progress as Record<string, string | number>;

  return (
    <div className="text-center py-12 space-y-4">
      <div className="flex justify-center">
        <Icon
          className={`h-12 w-12 ${isRunning ? "animate-spin text-primary" : ""} ${
            job.status === "completed" ? "text-green-500" : ""
          } ${job.status === "failed" ? "text-destructive" : ""}`}
        />
      </div>

      <div>
        <Badge variant={config.variant}>{config.label}</Badge>
        <p className="mt-2 text-sm text-muted-foreground">
          Job: {job.job_type.replace(/_/g, " ")}
        </p>
      </div>

      {Object.keys(progress).length > 0 && (
        <div className="text-sm text-muted-foreground space-y-1">
          {Object.entries(progress).map(([k, v]) => (
            <p key={k}>
              {k.replace(/_/g, " ")}: {String(v)}
            </p>
          ))}
        </div>
      )}

      {job.status === "completed" && job.channel_id && (
        <Button nativeButton={false} render={<Link href={`/channels/${(job.config as Record<string, string>)?.handle || job.channel_id}`} />}>
          View Channel
        </Button>
      )}

      {job.status === "failed" && job.error && (
        <p className="text-sm text-destructive max-w-md mx-auto">{job.error}</p>
      )}
    </div>
  );
}
