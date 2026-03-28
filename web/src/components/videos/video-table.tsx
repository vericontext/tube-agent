"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useVideos } from "@/hooks/use-videos";
import { formatNumber, formatDate, formatDuration } from "@/lib/utils";
import { ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";

const SORT_FIELDS = [
  { key: "published_at", label: "Date" },
  { key: "view_count", label: "Views" },
  { key: "like_count", label: "Likes" },
  { key: "comment_count", label: "Comments" },
] as const;

const PAGE_SIZE = 20;

export function VideoTable({ handle }: { handle: string }) {
  const [sortBy, setSortBy] = useState("published_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);

  const { data, isLoading } = useVideos(handle, {
    sort_by: sortBy,
    sort_order: sortOrder,
    offset: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(0);
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      {/* Mobile card view */}
      <div className="md:hidden space-y-3">
        {data?.videos.map((v) => (
          <Link
            key={v.video_id}
            href={`/channels/${handle}/videos/${v.video_id}`}
            className="block"
          >
            <div className="border rounded-lg p-3 hover:border-primary/50 transition-colors">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-medium line-clamp-2">{v.title}</h3>
                {v.has_summary && (
                  <Badge variant="secondary" className="shrink-0 text-xs">
                    Summary
                  </Badge>
                )}
              </div>
              <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
                <span>{formatDate(v.published_at)}</span>
                <span>{v.view_count != null ? `${formatNumber(v.view_count)} views` : "Data expired"}</span>
                <span>{formatDuration(v.duration_seconds)}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Desktop table view */}
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40%]">Title</TableHead>
              {SORT_FIELDS.map((f) => (
                <TableHead key={f.key}>
                  <button
                    onClick={() => toggleSort(f.key)}
                    className="flex items-center gap-1 hover:text-foreground"
                  >
                    {f.label}
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
              ))}
              <TableHead>Duration</TableHead>
              <TableHead>Summary</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.videos.map((v) => (
              <TableRow key={v.video_id} className="cursor-pointer">
                <TableCell>
                  <Link
                    href={`/channels/${handle}/videos/${v.video_id}`}
                    className="hover:underline line-clamp-1"
                  >
                    {v.title}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(v.published_at)}
                </TableCell>
                <TableCell>{v.view_count != null ? formatNumber(v.view_count) : <span className="text-muted-foreground text-xs">Data expired</span>}</TableCell>
                <TableCell>{v.like_count != null ? formatNumber(v.like_count) : <span className="text-muted-foreground text-xs">Data expired</span>}</TableCell>
                <TableCell>{v.comment_count != null ? formatNumber(v.comment_count) : <span className="text-muted-foreground text-xs">Data expired</span>}</TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDuration(v.duration_seconds)}
                </TableCell>
                <TableCell>
                  {v.has_summary && (
                    <Badge variant="secondary">Yes</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-muted-foreground">
            {total} videos total
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">
              {page + 1} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
