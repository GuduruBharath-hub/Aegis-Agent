"use client";

import { useCallback, useEffect, useState } from "react";

import { JobHeader } from "@/components/dashboard/JobHeader";
import { PipelineRail } from "@/components/dashboard/PipelineRail";
import { AttemptWorkbench } from "@/components/dashboard/AttemptWorkbench";
import { GuardrailList } from "@/components/dashboard/GuardrailList";
import { useJobStream } from "@/hooks/useJobStream";
import { VerdictBanner } from "@/components/dashboard/VerdictBanner";
import {
  getJob,
  listJobAttempts,
  type AttemptSummary,
  type Job,
} from "@/lib/api";

interface JobDashboardProps {
  jobId: string;
}

export function JobDashboard({ jobId }: JobDashboardProps) {
  const [job, setJob] = useState<Job | null>(null);
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextJob, nextAttempts] = await Promise.all([
        getJob(jobId),
        listJobAttempts(jobId),
      ]);
      setJob(nextJob);
      setAttempts(nextAttempts);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load job");
    }
  }, [jobId]);

  const stream = useJobStream(jobId, refresh);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      getJob(jobId, controller.signal),
      listJobAttempts(jobId, controller.signal),
    ]).then(
      ([initialJob, initialAttempts]) => {
        setJob(initialJob);
        setAttempts(initialAttempts);
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
      <AttemptWorkbench
        jobId={job.id}
        attempts={attempts}
        events={stream.events}
      />
      <div className="mx-auto grid max-w-[1500px] gap-4 px-5 pb-10 md:px-8">
        <VerdictBanner decision={job.final_decision} reason={job.final_reason} />
        <GuardrailList />
      </div>
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
