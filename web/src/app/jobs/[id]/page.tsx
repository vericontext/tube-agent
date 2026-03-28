"use client";

import { use } from "react";
import { useJob } from "@/hooks/use-job";
import { JobProgress } from "@/components/jobs/job-progress";

export default function JobPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: job, isLoading } = useJob(id);

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold text-center mb-6">Job Status</h1>
      <JobProgress job={job} isLoading={isLoading} />
    </div>
  );
}
