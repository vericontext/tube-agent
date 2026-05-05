import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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

  const mutation = useMutation({
    mutationFn: () =>
      api.channels.create({
        handle: handle.replace(/^@/, ""),
        max_videos: Number.parseInt(maxVideos, 10) || 100,
        skip_comments: true,
        skip_summaries: true,
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
          {mutation.isError && (
            <p className="text-sm text-destructive">
              {mutation.error instanceof Error ? mutation.error.message : "Failed to start indexing"}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={mutation.isPending || !handle.trim()}>
            {mutation.isPending ? "Starting…" : "Start indexing"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
