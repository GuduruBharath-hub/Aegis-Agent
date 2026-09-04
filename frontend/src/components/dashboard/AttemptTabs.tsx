import type { AttemptSummary } from "@/lib/api";

interface AttemptTabsProps {
  attempts: AttemptSummary[];
  selected: number;
  onSelect: (attempt: number) => void;
}

export function AttemptTabs({ attempts, selected, onSelect }: AttemptTabsProps) {
  return (
    <div
      aria-label="Patch attempts"
      className="flex gap-1 overflow-x-auto border-b border-zinc-800"
      role="tablist"
    >
      {attempts.map((attempt) => {
        const active = attempt.attempt === selected;
        return (
          <button
            aria-controls={`attempt-panel-${attempt.attempt}`}
            aria-label={`Attempt ${attempt.attempt}: ${attempt.decision.replaceAll("_", " ")}`}
            aria-selected={active}
            className={`group min-w-fit border-x border-t px-4 py-3 text-left font-mono transition-colors ${
              active
                ? "border-zinc-700 bg-zinc-900 text-zinc-100"
                : "border-transparent text-zinc-500 hover:bg-zinc-900/50 hover:text-zinc-300"
            }`}
            id={`attempt-tab-${attempt.attempt}`}
            key={attempt.attempt}
            onClick={() => onSelect(attempt.attempt)}
            role="tab"
            type="button"
          >
            <span className="text-xs">#{attempt.attempt}</span>
            <span className={`ml-2 text-[10px] uppercase tracking-wider ${decisionColor(attempt.decision)}`}>
              {attempt.decision.replaceAll("_", " ")}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function decisionColor(decision: AttemptSummary["decision"]): string {
  return {
    in_progress: "text-sky-300",
    rejected: "text-rose-300",
    verified: "text-emerald-300",
  }[decision];
}
