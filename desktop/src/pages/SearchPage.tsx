import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SearchResultCard } from "@/components/SearchResultCard";

export function SearchPage() {
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";

  const keyword = useQuery({
    queryKey: ["search", "keyword", q],
    queryFn: () => api.search.keyword(q, "all", 30),
    enabled: q.length > 0,
  });

  const semantic = useQuery({
    queryKey: ["search", "semantic", q],
    queryFn: () => api.search.semantic(q, undefined, 30),
    enabled: q.length > 0,
    retry: false,
  });

  if (!q) {
    return (
      <div className="container mx-auto px-6 py-10 text-sm text-muted-foreground">
        Type a query into the search bar above.
      </div>
    );
  }

  const semanticUnavailable =
    semantic.error instanceof ApiError && semantic.error.status === 503;

  return (
    <div className="container mx-auto px-6 py-10 max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-sm text-muted-foreground">Results for “{q}”</p>
      </div>

      <Tabs defaultValue="semantic">
        <TabsList>
          <TabsTrigger value="semantic">
            Semantic
            {semantic.data && (
              <span className="ml-2 text-xs text-muted-foreground">{semantic.data.results.length}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="keyword">
            Keyword
            {keyword.data && (
              <span className="ml-2 text-xs text-muted-foreground">{keyword.data.results.length}</span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="semantic" className="space-y-3">
          {semantic.isLoading && <p className="text-sm text-muted-foreground">Searching…</p>}
          {semanticUnavailable && (
            <p className="text-sm text-muted-foreground">
              Semantic search is preparing the embedding model. Try again in a moment, or use keyword search below.
            </p>
          )}
          {!semanticUnavailable && semantic.error && (
            <p className="text-sm text-destructive">Semantic search failed.</p>
          )}
          {semantic.data?.results.map((r, i) => (
            <SearchResultCard key={`${r.video_id}-${r.start_seconds}-${i}`} result={r} />
          ))}
          {semantic.data && semantic.data.results.length === 0 && (
            <p className="text-sm text-muted-foreground">No semantic matches yet.</p>
          )}
        </TabsContent>

        <TabsContent value="keyword" className="space-y-3">
          {keyword.isLoading && <p className="text-sm text-muted-foreground">Searching…</p>}
          {keyword.error && (
            <p className="text-sm text-destructive">Keyword search failed.</p>
          )}
          {keyword.data?.results.map((r, i) => (
            <SearchResultCard key={`${r.type}-${r.video_id}-${i}`} result={r} />
          ))}
          {keyword.data && keyword.data.results.length === 0 && (
            <p className="text-sm text-muted-foreground">No keyword matches.</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
