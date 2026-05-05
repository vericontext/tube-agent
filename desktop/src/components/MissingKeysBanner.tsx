import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CircleAlert } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function MissingKeysBanner() {
  const { data } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.system.getSettings(),
  });

  if (!data || data.youtube_api_key === "set") return null;

  return (
    <Card className="border-amber-500/30 bg-amber-500/5">
      <CardContent className="p-4 flex items-start gap-3">
        <CircleAlert className="size-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="font-medium text-sm">Add your YouTube API key to start indexing.</p>
          <p className="text-xs text-muted-foreground mt-1">
            Get a free key at console.cloud.google.com → APIs &amp; Services → Credentials, then drop it into Settings.
          </p>
        </div>
        <Button asChild size="sm">
          <Link to="/settings">Open settings</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
