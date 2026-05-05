"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import { useSearch } from "@/hooks/use-search";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ExternalLink } from "lucide-react";

function SearchResults() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const { data, isLoading } = useSearch(query);

  if (!query) {
    return (
      <p className="text-center py-12 text-muted-foreground">
        Enter a search query to find videos and summaries.
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <p className="text-center py-12 text-muted-foreground">
        No results found for &ldquo;{query}&rdquo;.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground mb-4">
        {data.total} results for &ldquo;{data.query}&rdquo;
      </p>
      {data.results.map((result, i) => (
        <Card key={i} className="hover:border-primary/50 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <Badge
                variant={result.type === "transcript" ? "default" : "secondary"}
                className="shrink-0"
              >
                {result.type}
              </Badge>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 min-w-0">
                  <Link
                    href={`/channels/${result.channel_handle || "_"}/videos/${result.video_id}`}
                    className="font-medium line-clamp-1 hover:underline"
                  >
                    {result.video_title || result.title}
                  </Link>
                  {result.timestamp && (
                    <span className="font-mono text-xs text-primary shrink-0">
                      {result.timestamp}
                    </span>
                  )}
                </div>
                {result.channel_handle && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    @{result.channel_handle}
                    {result.language ? ` · ${result.language}` : ""}
                  </p>
                )}
                <p className="text-sm text-muted-foreground line-clamp-3 mt-2">
                  {result.snippet}
                </p>
              </div>
              {result.youtube_url && (
                <a
                  href={result.youtube_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground hover:text-foreground shrink-0"
                  aria-label="Open timestamp on YouTube"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function SearchPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Search</h1>
      <Suspense
        fallback={
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        }
      >
        <SearchResults />
      </Suspense>
    </div>
  );
}
