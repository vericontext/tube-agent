import { useEffect, useState, type ReactNode } from "react";
import { Activity, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { waitForReady } from "@/lib/api";

type Status = "starting" | "ready" | "failed";

interface Props {
  children: ReactNode;
}

export function SidecarGate({ children }: Props) {
  const [status, setStatus] = useState<Status>("starting");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await waitForReady();
      if (cancelled) return;
      setStatus(ok ? "ready" : "failed");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "ready") return <>{children}</>;

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background text-foreground">
      <div className="flex items-center gap-3">
        <Activity className="size-6 text-emerald-500" />
        <h1 className="text-2xl font-semibold tracking-tight">Tube Agent</h1>
      </div>

      {status === "starting" && (
        <p className="text-sm text-muted-foreground flex items-center gap-2">
          <Loader2 className="size-4 animate-spin" />
          Starting backend…
        </p>
      )}

      {status === "failed" && (
        <div className="flex flex-col items-center gap-3">
          <p className="text-sm text-destructive">Backend did not respond.</p>
          <Button variant="outline" onClick={() => location.reload()}>
            Retry
          </Button>
        </div>
      )}
    </main>
  );
}
