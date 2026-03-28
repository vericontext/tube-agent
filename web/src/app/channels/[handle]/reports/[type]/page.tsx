"use client";

import { use } from "react";
import Link from "next/link";
import { useReport } from "@/hooks/use-reports";
import { ReportViewer } from "@/components/reports/report-viewer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft } from "lucide-react";

export default function ReportPage({
  params,
}: {
  params: Promise<{ handle: string; type: string }>;
}) {
  const { handle, type } = use(params);
  const { data: report, isLoading } = useReport(handle, type);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href={`/channels/${handle}`} />}>
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <Badge variant="secondary">{type.replace(/_/g, " ")}</Badge>
      </div>

      <ReportViewer content={report?.content_md} isLoading={isLoading} />
    </div>
  );
}
