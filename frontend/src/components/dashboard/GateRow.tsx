import type { AttemptDetail, GateResult } from "@/lib/api";

type GateName = keyof AttemptDetail["gates"];

interface GateDefinition {
  name: GateName;
  label: string;
  raw: keyof AttemptDetail["raw"] | null;
}

const GATES: GateDefinition[] = [
  { name: "security", label: "Security", raw: "harness" },
  { name: "regression", label: "Regression", raw: "pytest" },
  { name: "post_scan", label: "Post-SAST", raw: "bandit" },
  { name: "policy", label: "Policy", raw: null },
  { name: "integrity", label: "Integrity", raw: null },
  { name: "explain", label: "Explain", raw: null },
];

interface GateRowProps {
  attempt: AttemptDetail;
}

export function GateRow({ attempt }: GateRowProps) {
  return (
    <section aria-labelledby="gates-heading" className="mt-7">
      <div className="mb-3 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-600">
            Independent controls
          </p>
          <h3 id="gates-heading" className="mt-1 text-sm font-medium text-zinc-300">
            Attempt {attempt.attempt} gate evidence
          </h3>
        </div>
        <p className="font-mono text-[9px] uppercase tracking-wider text-zinc-600">
          Evidence only · server evaluated
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {GATES.map((gate) => {
          const result = attempt.gates[gate.name];
          const raw = gate.raw ? attempt.raw[gate.raw] : null;
          return (
            <GateCard
              key={gate.name}
              label={gate.label}
              raw={raw ?? JSON.stringify(result, null, 2)}
              result={result}
            />
          );
        })}
      </div>
    </section>
  );
}

interface GateCardProps {
  label: string;
  result: GateResult;
  raw: string;
}

function GateCard({ label, result, raw }: GateCardProps) {
  const status =
    result.passed === true ? "passed" : result.passed === false ? "failed" : "not run";
  const reason =
    typeof result.reason === "string"
      ? result.reason
      : status === "not run"
        ? "No evidence was recorded for this gate."
        : "Gate result recorded without a reason.";

  return (
    <article className="flex min-h-44 flex-col border border-zinc-800 bg-zinc-950 px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="font-mono text-[11px] uppercase tracking-[0.16em] text-zinc-300">
          {label}
        </h4>
        <span className={`border px-2 py-1 font-mono text-[9px] uppercase tracking-wider ${statusColor(status)}`}>
          {status}
        </span>
      </div>
      <p className="mt-4 flex-1 text-xs leading-5 text-zinc-500">{reason}</p>
      <details className="group mt-4 border-t border-zinc-900 pt-3">
        <summary className="cursor-pointer select-none font-mono text-[9px] uppercase tracking-[0.16em] text-zinc-600 hover:text-zinc-300">
          Raw evidence
        </summary>
        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words bg-zinc-900 p-3 font-mono text-[10px] leading-5 text-zinc-400">
          {raw || "No raw artifact was retained."}
        </pre>
      </details>
    </article>
  );
}

function statusColor(status: "passed" | "failed" | "not run"): string {
  return {
    passed: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
    failed: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    "not run": "border-zinc-700 bg-zinc-900 text-zinc-500",
  }[status];
}
