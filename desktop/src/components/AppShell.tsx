import { Activity, Search, Settings } from "lucide-react";
import { Link, Outlet, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Input } from "@/components/ui/input";
import { SemanticReadinessPill } from "@/components/SemanticReadinessPill";
import { api } from "@/lib/api";

export function AppShell() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState("");

  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.system.getSettings(),
  });
  const needsAttention = settings?.youtube_api_key === "unset";

  // Keep the input in sync when navigating directly to /search?q=...
  useEffect(() => {
    setQuery(searchParams.get("q") ?? "");
  }, [searchParams]);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="container mx-auto flex h-14 items-center gap-4 px-6">
          <Link to="/" className="flex items-center gap-2 font-semibold shrink-0">
            <Activity className="size-5 text-emerald-500" />
            <span>Tube Agent</span>
          </Link>
          <form
            className="flex-1 max-w-xl"
            onSubmit={(e) => {
              e.preventDefault();
              const q = query.trim();
              if (q) navigate(`/search?q=${encodeURIComponent(q)}`);
            }}
          >
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search transcripts…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9 h-9"
              />
            </div>
          </form>
          <Link
            to="/settings"
            className="relative inline-flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Settings"
          >
            <Settings className="size-5" />
            {needsAttention && (
              <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-red-500 ring-2 ring-background" />
            )}
          </Link>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <SemanticReadinessPill />
    </div>
  );
}
