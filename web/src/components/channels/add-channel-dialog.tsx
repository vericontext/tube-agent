"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { Plus } from "lucide-react";

export function AddChannelDialog() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [handle, setHandle] = useState("");
  const [maxVideos, setMaxVideos] = useState("100");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const job = await api.channels.create({
        handle: handle.replace("@", ""),
        max_videos: parseInt(maxVideos) || 100,
        skip_comments: true,
        skip_summaries: true,
        fetch_transcripts: true,
        transcript_languages: ["ko", "en"],
      });
      setOpen(false);
      setHandle("");
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>
        <Plus className="h-4 w-4 mr-2" />
        Add Channel
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Index YouTube Channel</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium">Channel Handle</label>
            <Input
              placeholder="e.g. ycombinator"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm font-medium">Max Videos</label>
            <Input
              type="number"
              min="1"
              max="1000"
              value={maxVideos}
              onChange={(e) => setMaxVideos(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={loading || !handle.trim()} className="w-full">
            {loading ? "Starting..." : "Start Indexing"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
