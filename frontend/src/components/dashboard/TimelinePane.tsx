import type { JobEvent } from "@/lib/api";

interface TimelinePaneProps {
  attempt: number;
  events: JobEvent[];
}

export function TimelinePane({ attempt, events }: TimelinePaneProps) {
  const attemptEvents = events
    .filter((event) => event.attempt === attempt)
    .reverse();

  return (
    <section aria-labelledby="timeline-heading" className="min-h-[420px] border border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 px-4 py-3">
        <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-600">
          Durable event log
        </p>
        <h3 id="timeline-heading" className="mt-1 text-sm font-medium text-zinc-300">
          Attempt {attempt} timeline
        </h3>
      </div>
      {attemptEvents.length ? (
        <ol className="divide-y divide-zinc-900">
          {attemptEvents.map((event) => (
            <li className="grid grid-cols-[64px_10px_1fr] gap-3 px-4 py-3" key={event.seq}>
              <time className="font-mono text-[10px] text-zinc-600" dateTime={event.ts}>
                {clock(event.ts)}
              </time>
              <span
                aria-label={`${event.severity} event`}
                className={`mt-1 h-2 w-2 rounded-full ${severityColor(event.severity)}`}
              />
              <div className="min-w-0">
                <p className="text-xs font-medium text-zinc-300">{event.title}</p>
                {event.message ? (
                  <p className="mt-1 text-[11px] leading-5 text-zinc-500">{event.message}</p>
                ) : null}
                <p className="mt-1 font-mono text-[9px] uppercase tracking-wider text-zinc-700">
                  {event.type.replaceAll("_", " ")}
                </p>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="px-4 py-8 font-mono text-xs text-zinc-600">
          No attempt-scoped events recorded yet.
        </p>
      )}
    </section>
  );
}

function clock(timestamp: string): string {
  const match = timestamp.match(/T(\d{2}:\d{2}:\d{2})/);
  return match?.[1] ?? timestamp;
}

function severityColor(severity: JobEvent["severity"]): string {
  return {
    info: "bg-sky-400",
    success: "bg-emerald-400",
    warning: "bg-amber-400",
    critical: "bg-rose-400",
  }[severity];
}
