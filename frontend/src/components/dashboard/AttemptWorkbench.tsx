"use client";

import { useEffect, useState } from "react";

import { AttemptTabs } from "@/components/dashboard/AttemptTabs";
import { DiffPane } from "@/components/dashboard/DiffPane";
import { GateRow } from "@/components/dashboard/GateRow";
import { TimelinePane } from "@/components/dashboard/TimelinePane";
import {
  getJobAttempt,
  type AttemptDetail,
  type AttemptSummary,
  type JobEvent,
} from "@/lib/api";

interface AttemptWorkbenchProps {
  jobId: string;
  attempts: AttemptSummary[];
  events: JobEvent[];
}

interface LoadedAttempt {
  number: number;
  detail: AttemptDetail;
}

export function AttemptWorkbench({ jobId, attempts, events }: AttemptWorkbenchProps) {
  const [chosen, setChosen] = useState<number | null>(null);
  const [loaded, setLoaded] = useState<LoadedAttempt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = attempts.some((attempt) => attempt.attempt === chosen)
    ? chosen
    : (attempts.at(-1)?.attempt ?? null);

  useEffect(() => {
    if (selected === null) return;
    const controller = new AbortController();
    void getJobAttempt(jobId, selected, controller.signal).then(
      (detail) => {
        setLoaded({ number: selected, detail });
        setError(null);
      },
      (cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : "Unable to load attempt");
        }
      },
    );
    return () => controller.abort();
  }, [jobId, selected, attempts]);

  if (selected === null) {
    return (
      <main className="mx-auto max-w-[1500px] px-5 py-8 md:px-8">
        <div className="border border-dashed border-zinc-800 px-6 py-12 text-center font-mono text-xs text-zinc-600">
          Waiting for the first patch attempt…
        </div>
      </main>
    );
  }

  const detail = loaded?.number === selected ? loaded.detail : null;
  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8 md:px-8">
      <AttemptTabs attempts={attempts} selected={selected} onSelect={setChosen} />
      <div
        aria-labelledby={`attempt-tab-${selected}`}
        className="mt-4"
        id={`attempt-panel-${selected}`}
        role="tabpanel"
      >
        {detail ? (
          <>
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,0.8fr)]">
              <DiffPane attempt={detail} />
              <TimelinePane attempt={selected} events={events} />
            </div>
            <GateRow attempt={detail} />
          </>
        ) : (
          <div className="border border-zinc-800 bg-zinc-900 px-6 py-10 font-mono text-xs text-zinc-500">
            {error ?? `Loading attempt ${selected} evidence…`}
          </div>
        )}
      </div>
    </main>
  );
}
