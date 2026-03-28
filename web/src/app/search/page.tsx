"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import { useSearch } from "@/hooks/use-search";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

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
      <p className="text-xs text-muted-foreground">
        Search results are based on AI-generated analysis data, not original YouTube content.
      </p>
      {data.results.map((result, i) => (
        <Link key={i} href={`/channels/_/videos/${result.video_id}`}>
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Badge
                  variant={result.type === "video" ? "default" : "secondary"}
                >
                  {result.type}
                </Badge>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium line-clamp-1">{result.title}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                    {result.snippet}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
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
