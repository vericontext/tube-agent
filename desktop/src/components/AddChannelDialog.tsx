import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

export function AddChannelDialog() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [handle, setHandle] = useState("");
  const [maxVideos, setMaxVideos] = useState("100");
  const [generateSummaries, setGenerateSummaries] = useState(true);

  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.system.getSettings(),
  });
  const youtubeKeyMissing = settings?.youtube_api_key === "unset";
  const geminiKeyMissing = settings?.gemini_api_key === "unset";
  const shouldGenerateSummaries = generateSummaries && !geminiKeyMissing;

  const mutation = useMutation({
    mutationFn: () =>
      api.channels.create({
        handle: handle.replace(/^@/, ""),
        max_videos: Number.parseInt(maxVideos, 10) || 100,
        skip_comments: true,
        skip_summaries: !shouldGenerateSummaries,
        summary_max: 10,
        summary_mode: "transcript",
        summary_language: "en",
        fetch_transcripts: true,
        transcript_languages: ["ko", "en"],
      }),
    onSuccess: (job) => {
      setOpen(false);
      setHandle("");
      queryClient.invalidateQueries({ queryKey: ["channels"] });
      navigate(`/jobs/${job.id}`);
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="size-4" />
          Add channel
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Index a YouTube channel</DialogTitle>
        </DialogHeader>
        {youtubeKeyMissing ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              You need to add a YouTube Data API key before indexing channels. The key is stored on this device only.
            </p>
            <Button asChild className="w-full">
              <Link to="/settings" onClick={() => setOpen(false)}>
                Open settings
              </Link>
            </Button>
          </div>
        ) : (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (handle.trim()) mutation.mutate();
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="handle">Channel handle</Label>
            <Input
              id="handle"
              placeholder="ycombinator"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="max_videos">Max videos</Label>
            <Input
              id="max_videos"
              type="number"
              min={1}
              max={1000}
              value={maxVideos}
              onChange={(e) => setMaxVideos(e.target.value)}
            />
          </div>
          <label className="flex items-start gap-3 rounded-md border px-3 py-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={generateSummaries && !geminiKeyMissing}
              disabled={geminiKeyMissing}
              onChange={(e) => setGenerateSummaries(e.target.checked)}
            />
            <span>
              <span className="block font-medium">Generate summaries for latest 10 videos</span>
              <span className="block text-xs text-muted-foreground">
                {geminiKeyMissing
                  ? "Add a Gemini API key in Settings to enable transcript-based summaries."
                  : "Uses saved transcripts and Gemini text generation. Results are stored locally."}
              </span>
            </span>
          </label>
          {geminiKeyMissing && (
            <Button asChild variant="outline" className="w-full">
              <Link to="/settings" onClick={() => setOpen(false)}>
                Add Gemini key
              </Link>
            </Button>
          )}
          {mutation.isError && (
            <p className="text-sm text-destructive">
              {mutation.error instanceof Error ? mutation.error.message : "Failed to start indexing"}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={mutation.isPending || !handle.trim()}>
            {mutation.isPending ? "Starting…" : "Start indexing"}
          </Button>
        </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
