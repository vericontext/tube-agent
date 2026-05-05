import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, Loader2 } from "lucide-react";

import { getApiBase } from "@/lib/api";

type EmbeddingStatus = "idle" | "loading" | "ready" | "failed";

interface StatusResponse {
  status: EmbeddingStatus;
  model: string | null;
  error: string | null;
}

export function SemanticReadinessPill() {
  const [state, setState] = useState<StatusResponse>({
    status: "idle",
    model: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = async () => {
      try {
        const base = await getApiBase();
        const res = await fetch(`${base}/system/embedding-status`);
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data: StatusResponse = await res.json();
        if (cancelled) return;
        setState(data);
        if (data.status === "ready") return; // stop polling
      } catch {
        // sidecar not ready yet — keep polling
      }
      if (!cancelled) timer = setTimeout(tick, 1500);
    };
    tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  const retry = async () => {
    try {
      const base = await getApiBase();
      await fetch(`${base}/system/embedding/prepare`, { method: "POST" });
      setState((s) => ({ ...s, status: "loading", error: null }));
    } catch {
      // ignore — pill will stay in failed state
    }
  };

  if (state.status === "ready") return null;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="flex items-center gap-2 rounded-full bg-background border shadow-sm px-3 py-1.5 text-xs">
        {state.status === "loading" || state.status === "idle" ? (
          <>
            <Loader2 className="size-3 animate-spin text-emerald-500" />
            <span className="text-muted-foreground">Preparing semantic search…</span>
          </>
        ) : state.status === "failed" ? (
          <>
            <CircleAlert className="size-3 text-destructive" />
            <span className="text-muted-foreground">Semantic offline</span>
            <button
              type="button"
              className="text-foreground hover:underline"
              onClick={retry}
            >
              retry
            </button>
          </>
        ) : (
          <>
            <CheckCircle2 className="size-3 text-emerald-500" />
            <span className="text-muted-foreground">Semantic ready</span>
          </>
        )}
      </div>
    </div>
  );
}
