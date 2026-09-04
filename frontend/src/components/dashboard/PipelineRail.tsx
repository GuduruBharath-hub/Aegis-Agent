import type { Job, JobEvent, JobState } from "@/lib/api";

type StageStatus = "waiting" | "active" | "passed" | "rejected" | "skipped";

interface Stage {
  id: "detect" | "reproduce" | "context" | "patch" | "policy" | "sandbox" | "verify" | "deliver";
  label: string;
  states: JobState[];
  passEvents: string[];
  failEvents: string[];
}

const STAGES: Stage[] = [
  {
    id: "detect",
    label: "Detect",
    states: ["received", "scanning", "finding_identified"],
    passEvents: ["finding_detected"],
    failEvents: [],
  },
  {
    id: "reproduce",
    label: "Reproduce",
    states: ["reproducing", "reproduced"],
    passEvents: ["reproduction_confirmed"],
    failEvents: [],
  },
  {
    id: "context",
    label: "Context",
    states: ["context_building"],
    passEvents: ["context_built"],
    failEvents: ["technical_error"],
  },
  {
    id: "patch",
    label: "Patch",
    states: ["generating_patch", "retrying"],
    passEvents: ["patch_generated"],
    failEvents: [],
  },
  {
    id: "policy",
    label: "Policy",
    states: ["validating_patch"],
    passEvents: ["policy_passed"],
    failEvents: ["policy_failed"],
  },
  {
    id: "sandbox",
    label: "Sandbox",
    states: ["sandboxing"],
    passEvents: ["sandbox_completed"],
    failEvents: [],
  },
  {
    id: "verify",
    label: "Verify",
    states: [
      "verifying_security",
      "verifying_regression",
      "post_scanning",
      "integrity_check",
      "verified",
    ],
    passEvents: ["verified"],
    failEvents: [
      "security_failed",
      "regression_failed",
      "post_scan_failed",
      "integrity_failed",
      "explain_failed",
      "candidate_rejected",
    ],
  },
  {
    id: "deliver",
    label: "Deliver",
    states: ["creating_pr", "completed"],
    passEvents: [],
    failEvents: [],
  },
];

const TERMINAL_STATES = new Set<JobState>([
  "completed",
  "escalated",
  "policy_rejected",
  "failed",
]);

interface PipelineRailProps {
  job: Job;
  events: JobEvent[];
}

export function PipelineRail({ job, events }: PipelineRailProps) {
  const retryCount = new Set(
    events
      .filter((event) => event.type === "candidate_rejected")
      .map((event) => event.attempt)
      .filter((attempt): attempt is number => attempt !== null),
  ).size;

  return (
    <section aria-labelledby="pipeline-heading" className="border-b border-zinc-800 bg-zinc-950 px-5 py-7 md:px-8">
      <div className="mx-auto max-w-[1500px]">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-zinc-600">
              Trusted execution path
            </p>
            <h2 id="pipeline-heading" className="mt-1 text-sm font-medium text-zinc-300">
              Remediation pipeline
            </h2>
          </div>
          <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-600">
            Server state: {job.state.replaceAll("_", " ")}
          </p>
        </div>

        <div className="mt-7 overflow-x-auto pb-2">
          <div className="min-w-[900px]">
            <ol className="grid grid-cols-8">
              {STAGES.map((stage, index) => {
                const status = statusFor(stage, index, job, events);
                return (
                  <li key={stage.id} className="relative pr-2 last:pr-0">
                    {index < STAGES.length - 1 ? (
                      <span className="absolute left-7 right-0 top-3 h-px bg-zinc-800" aria-hidden="true" />
                    ) : null}
                    <div className="relative flex items-center gap-2 bg-zinc-950 pr-2">
                      <span className={`h-6 w-6 border text-center font-mono text-[10px] leading-[22px] ${statusColor(status)}`}>
                        {index + 1}
                      </span>
                      <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-300">
                        {stage.label}
                      </span>
                    </div>
                    <p className={`ml-8 mt-2 font-mono text-[9px] uppercase tracking-widest ${statusText(status)}`}>
                      {status}
                    </p>
                  </li>
                );
              })}
            </ol>

            {retryCount > 0 ? (
              <div className="mt-4 grid grid-cols-8" aria-label={`Retry ${retryCount}: verification returned to patch generation`}>
                <div className="col-span-4 col-start-4 flex h-10 items-end px-3">
                  <div className="relative h-7 w-full rounded-b-xl border-x border-b border-amber-500/50">
                    <span className="absolute -left-1 -top-1 text-sm text-amber-300" aria-hidden="true">
                      ↑
                    </span>
                    <span className="absolute inset-x-0 top-2 text-center font-mono text-[9px] uppercase tracking-[0.2em] text-amber-300">
                      Retry {retryCount} · attempt {job.current_attempt || retryCount + 1}/{job.max_attempts}
                    </span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}

function statusFor(stage: Stage, index: number, job: Job, events: JobEvent[]): StageStatus {
  if (job.state === "completed") return "passed";
  if (stage.states.includes(job.state)) return "active";

  const latestRelevant = events.findLast(
    (event) => stage.passEvents.includes(event.type) || stage.failEvents.includes(event.type),
  );
  if (latestRelevant && stage.failEvents.includes(latestRelevant.type)) return "rejected";
  if (latestRelevant) return "passed";

  const activeIndex = STAGES.findIndex((candidate) => candidate.states.includes(job.state));
  if (activeIndex > index) return "passed";
  if (TERMINAL_STATES.has(job.state)) return "skipped";
  return "waiting";
}

function statusColor(status: StageStatus): string {
  return {
    waiting: "border-zinc-800 bg-zinc-950 text-zinc-600",
    active: "border-sky-400 bg-sky-400/10 text-sky-300 shadow-[0_0_12px_rgba(56,189,248,0.2)]",
    passed: "border-emerald-500/60 bg-emerald-500/10 text-emerald-300",
    rejected: "border-rose-500/60 bg-rose-500/10 text-rose-300",
    skipped: "border-zinc-800 bg-zinc-900 text-zinc-500",
  }[status];
}

function statusText(status: StageStatus): string {
  return {
    waiting: "text-zinc-700",
    active: "text-sky-300",
    passed: "text-emerald-400",
    rejected: "text-rose-400",
    skipped: "text-zinc-600",
  }[status];
}
