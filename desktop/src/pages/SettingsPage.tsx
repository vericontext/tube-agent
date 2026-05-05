import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, Loader2 } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Provider = "youtube" | "gemini";

interface ProviderConfig {
  id: Provider;
  title: string;
  helper: string;
  status: "set" | "unset";
}

export function SettingsPage() {
  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.system.getSettings(),
  });

  if (settings.isLoading) {
    return (
      <div className="container mx-auto px-6 py-10 text-sm text-muted-foreground">
        Loading settings…
      </div>
    );
  }

  if (settings.isError || !settings.data) {
    return (
      <div className="container mx-auto px-6 py-10 text-sm text-destructive">
        Could not load settings.
      </div>
    );
  }

  const providers: ProviderConfig[] = [
    {
      id: "youtube",
      title: "YouTube Data API v3",
      helper: "Required to index channels. Create a key at console.cloud.google.com.",
      status: settings.data.youtube_api_key,
    },
    {
      id: "gemini",
      title: "Google Gemini API",
      helper: "Optional. Only needed for the multimodal video summary stage.",
      status: settings.data.gemini_api_key,
    },
  ];

  return (
    <div className="container mx-auto px-6 py-10 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Keys are stored on this device at <code className="text-xs">{settings.data.app_data_dir}/secrets.json</code>.
        </p>
      </div>

      <div className="space-y-4">
        {providers.map((p) => (
          <ProviderCard key={p.id} provider={p} />
        ))}
      </div>
    </div>
  );
}

function ProviderCard({ provider }: { provider: ProviderConfig }) {
  const queryClient = useQueryClient();
  const [value, setValue] = useState("");
  const [testResult, setTestResult] = useState<{ ok: boolean; error: string | null } | null>(null);

  const save = useMutation({
    mutationFn: () =>
      api.system.updateSettings(
        provider.id === "youtube"
          ? { youtube_api_key: value }
          : { gemini_api_key: value },
      ),
    onSuccess: () => {
      setValue("");
      setTestResult(null);
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      queryClient.invalidateQueries({ queryKey: ["channels"] });
    },
  });

  const clear = useMutation({
    mutationFn: () =>
      api.system.updateSettings(
        provider.id === "youtube" ? { youtube_api_key: "" } : { gemini_api_key: "" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const test = useMutation({
    mutationFn: () =>
      api.system.testKey({ provider: provider.id, api_key: value }),
    onSuccess: (result) => setTestResult(result),
  });

  return (
    <Card>
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold leading-tight">{provider.title}</h2>
            <p className="text-xs text-muted-foreground mt-1">{provider.helper}</p>
          </div>
          <span
            className={
              "shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium " +
              (provider.status === "set"
                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                : "bg-muted text-muted-foreground")
            }
          >
            {provider.status === "set" ? "Configured" : "Not set"}
          </span>
        </div>

        <div className="space-y-2">
          <Label htmlFor={`${provider.id}-key`}>API key</Label>
          <Input
            id={`${provider.id}-key`}
            type="password"
            placeholder={provider.status === "set" ? "•••••••••••••••• (replace to update)" : "Paste key"}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setTestResult(null);
            }}
            autoComplete="off"
          />
        </div>

        {testResult && (
          <div
            className={
              "flex items-start gap-2 text-xs " +
              (testResult.ok ? "text-emerald-600 dark:text-emerald-400" : "text-destructive")
            }
          >
            {testResult.ok ? (
              <CheckCircle2 className="size-4 shrink-0 mt-0.5" />
            ) : (
              <CircleAlert className="size-4 shrink-0 mt-0.5" />
            )}
            <span>{testResult.ok ? "Key works." : testResult.error ?? "Invalid key."}</span>
          </div>
        )}

        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={!value.trim() || test.isPending}
            onClick={() => test.mutate()}
          >
            {test.isPending ? <Loader2 className="size-4 animate-spin" /> : "Test"}
          </Button>
          <Button disabled={!value.trim() || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
          {provider.status === "set" && (
            <Button
              variant="ghost"
              className="ml-auto text-muted-foreground"
              disabled={clear.isPending}
              onClick={() => clear.mutate()}
            >
              Clear
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
