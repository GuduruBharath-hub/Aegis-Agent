import type { Job } from "@/lib/api";

interface JobHeaderProps {
  job: Job;
  connection: "connecting" | "live" | "reconnecting" | "closed";
}

export function JobHeader({ job, connection }: JobHeaderProps) {
  return (
    <header className="border-b border-zinc-800 bg-zinc-950/90 px-5 py-5 backdrop-blur md:px-8">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-start justify-between gap-5">
        <div>
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,0.8)]" />
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-zinc-500">
              AegisAgent / remediation control plane
            </p>
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">
            {job.repository}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-zinc-500">
            <span title={job.base_sha}>base {shortSha(job.base_sha)}</span>
            <span aria-hidden="true">/</span>
            <span>{job.finding?.cwe ?? "finding pending"}</span>
            {job.finding ? (
              <>
                <span aria-hidden="true">/</span>
                <span>
                  {job.finding.file}:{job.finding.line}
                </span>
              </>
            ) : null}
          </div>
        </div>

        <dl className="flex flex-wrap items-center justify-end gap-2 font-mono text-[11px] uppercase tracking-wider">
          <Badge label="severity" value={job.finding?.severity ?? "pending"} tone="critical" />
          <Badge
            label="attempt"
            value={`${job.current_attempt}/${job.max_attempts}`}
            tone="neutral"
          />
          <Badge label="state" value={humanize(job.state)} tone="active" />
          <Badge label="sandbox" value={job.sandbox_tier ?? "pending"} tone="neutral" />
          <Badge
            label="stream"
            value={connection}
            tone={connection === "live" ? "success" : "neutral"}
          />
        </dl>
      </div>
    </header>
  );
}

interface BadgeProps {
  label: string;
  value: string;
  tone: "active" | "critical" | "neutral" | "success";
}

function Badge({ label, value, tone }: BadgeProps) {
  const colors = {
    active: "border-sky-500/40 bg-sky-500/10 text-sky-300",
    critical: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    neutral: "border-zinc-700 bg-zinc-900 text-zinc-300",
    success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  }[tone];
  return (
    <div className={`border px-2.5 py-1.5 ${colors}`}>
      <dt className="sr-only">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function humanize(value: string): string {
  return value.replaceAll("_", " ");
}

function shortSha(value: string): string {
  return value === "HEAD" ? value : value.slice(0, 9);
}
