import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import type { SearchResult } from "@/lib/types";

interface Props {
  result: SearchResult;
}

export function SearchResultCard({ result }: Props) {
  const detailHref =
    result.channel_handle
      ? `/channels/${result.channel_handle}/videos/${result.video_id}${
          result.start_seconds != null ? `?t=${Math.floor(result.start_seconds)}` : ""
        }`
      : null;

  return (
    <Card className="transition hover:border-foreground/40">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="rounded-full bg-muted px-2 py-0.5 capitalize">{result.type}</span>
          {result.channel_handle && (
            <Link to={`/channels/${result.channel_handle}`} className="hover:underline">
              @{result.channel_handle}
            </Link>
          )}
          {result.timestamp && <span className="tabular-nums">{result.timestamp}</span>}
          {result.score > 0 && (
            <span className="ml-auto text-[10px] tabular-nums text-muted-foreground/70">
              score {result.score.toFixed(3)}
            </span>
          )}
        </div>
        {detailHref ? (
          <Link to={detailHref} className="block font-medium leading-tight hover:underline">
            {result.video_title || result.title}
          </Link>
        ) : (
          <a
            href={`https://www.youtube.com/watch?v=${result.video_id}`}
            target="_blank"
            rel="noreferrer"
            className="block font-medium leading-tight hover:underline"
          >
            {result.video_title || result.title}
          </a>
        )}
        <p className="text-sm text-muted-foreground line-clamp-3">{result.snippet}</p>
      </CardContent>
    </Card>
  );
}
