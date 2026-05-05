import { useEffect, useState } from "react";
import { Activity, Loader2 } from "lucide-react";
import { getApiBase, waitForReady } from "@/lib/api";

type Status = "starting" | "ready" | "failed";

export default function App() {
  const [status, setStatus] = useState<Status>("starting");
  const [base, setBase] = useState<string>("");
  const [channels, setChannels] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const apiBase = await getApiBase();
        if (cancelled) return;
        setBase(apiBase);
        const ok = await waitForReady();
        if (cancelled) return;
        if (!ok) {
          setStatus("failed");
          return;
        }
        setStatus("ready");
        const res = await fetch(`${apiBase}/channels`);
        const data = await res.json();
        if (cancelled) return;
        setChannels(data);
      } catch (e) {
        if (!cancelled) setStatus("failed");
        console.error(e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-4 bg-zinc-950 text-zinc-100 px-6 py-10">
      <div className="flex items-center gap-3">
        <Activity className="size-6 text-emerald-400" />
        <h1 className="text-3xl font-semibold tracking-tight">Tube Agent</h1>
      </div>

      {status === "starting" && (
        <p className="text-sm text-zinc-400 flex items-center gap-2">
          <Loader2 className="size-4 animate-spin" />
          Starting sidecar…
        </p>
      )}

      {status === "ready" && (
        <div className="text-sm text-zinc-300 max-w-xl space-y-2 font-mono">
          <p className="text-emerald-400">sidecar ready</p>
          <p className="text-zinc-500">api base: {base}</p>
          <pre className="bg-zinc-900 p-3 rounded text-xs overflow-x-auto">
            {JSON.stringify(channels, null, 2)}
          </pre>
        </div>
      )}

      {status === "failed" && (
        <p className="text-sm text-red-400">
          Sidecar failed to come up. Check the dev console.
        </p>
      )}
    </main>
  );
}
