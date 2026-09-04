"use client";

import { useCallback, useEffect, useState } from "react";

import { JobHeader } from "@/components/dashboard/JobHeader";
import { PipelineRail } from "@/components/dashboard/PipelineRail";
import { useJobStream } from "@/hooks/useJobStream";
import { getJob, type Job } from "@/lib/api";

interface JobDashboardProps {
  jobId: string;
}

export function JobDashboard({ jobId }: JobDashboardProps) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setJob(await getJob(jobId));
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load job");
    }
  }, [jobId]);

  const stream = useJobStream(jobId, refresh);

  useEffect(() => {
    const controller = new AbortController();
    void getJob(jobId, controller.signal).then(
      (initialJob) => {
        setJob(initialJob);
        setError(null);
      },
      (cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : "Unable to load job");
        }
      },
    );
    return () => controller.abort();
  }, [jobId]);

  if (!job) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-8 text-zinc-300">
        <div className="border border-zinc-800 bg-zinc-900 px-8 py-7 font-mono text-sm">
          <span className="mr-3 inline-block h-2 w-2 animate-pulse bg-sky-400" />
          {error ?? "Loading durable job state…"}
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <JobHeader job={job} connection={stream.status} />
      <PipelineRail job={job} events={stream.events} />
      {stream.error ? (
        <div className="mx-auto mt-4 max-w-[1500px] px-5 md:px-8">
          <p className="border border-amber-500/30 bg-amber-500/10 px-4 py-3 font-mono text-xs text-amber-200">
            {stream.error}
          </p>
        </div>
      ) : null}
    </div>
  );
}
