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
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Plus } from "lucide-react";

export function AddChannelDialog() {
  const router = useRouter();
  const { session } = useAuth();
  const [open, setOpen] = useState(false);
  const [handle, setHandle] = useState("");
  const [maxVideos, setMaxVideos] = useState("100");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) {
      router.push("/login");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const job = await api.channels.create(
        {
          handle: handle.replace("@", ""),
          max_videos: parseInt(maxVideos) || 100,
        },
        session.access_token,
      );
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
          <DialogTitle>Analyze YouTube Channel</DialogTitle>
        </DialogHeader>
        {!session ? (
          <div className="text-center py-4">
            <p className="text-muted-foreground mb-4">
              Sign in to start analyzing channels
            </p>
            <Button onClick={() => { setOpen(false); router.push("/login"); }}>
              Sign In
            </Button>
          </div>
        ) : (
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
              {loading ? "Starting..." : "Start Analysis"}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
