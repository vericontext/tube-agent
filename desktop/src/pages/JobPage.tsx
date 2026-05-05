import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Loader2, CircleAlert, CheckCircle2 } from "lucide-react";

import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function JobPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: job, isError } = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.jobs.get(id!),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
  });

  useEffect(() => {
    if (job?.status === "completed" && job.config?.handle) {
      const handle = String(job.config.handle);
      const t = setTimeout(() => navigate(`/channels/${handle}`), 1200);
      return () => clearTimeout(t);
    }
  }, [job?.status, job?.config, navigate]);

  if (!id) return null;

  return (
    <div className="container mx-auto px-6 py-10 max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Indexing</h1>
      {isError && <p className="text-sm text-destructive">Could not load job.</p>}
      {job && (
        <Card>
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center gap-3">
              {job.status === "running" || job.status === "pending" ? (
                <Loader2 className="size-5 animate-spin text-emerald-500" />
              ) : job.status === "completed" ? (
                <CheckCircle2 className="size-5 text-emerald-500" />
              ) : (
                <CircleAlert className="size-5 text-destructive" />
              )}
              <div>
                <p className="font-medium capitalize">{job.status}</p>
                <p className="text-xs text-muted-foreground">
                  @{String(job.config?.handle ?? "")} · max {String(job.config?.max_videos ?? "—")} videos
                </p>
              </div>
            </div>

            {job.progress && Object.keys(job.progress).length > 0 && (
              <pre className="text-xs bg-muted rounded p-3 overflow-x-auto">
                {JSON.stringify(job.progress, null, 2)}
              </pre>
            )}

            {job.error && (
              <p className="text-sm text-destructive whitespace-pre-wrap">{job.error}</p>
            )}

            {job.status === "completed" && Boolean(job.config?.handle) && (
              <Button onClick={() => navigate(`/channels/${String(job.config?.handle)}`)}>
                Go to channel
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
