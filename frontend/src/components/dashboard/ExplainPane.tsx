import type { DiffLineSelection } from "@/components/dashboard/DiffPane";
import type { AttemptDetail, LineRationale } from "@/lib/api";

interface ExplainPaneProps {
  attempt: AttemptDetail;
  selection: DiffLineSelection | null;
}

export function ExplainPane({ attempt, selection }: ExplainPaneProps) {
  const rationale = attempt.rationale;
  const lineRationale = selection
    ? findLineRationale(rationale?.line_rationales ?? [], selection)
    : null;

  return (
    <section aria-labelledby="explain-heading" className="border border-zinc-800 bg-zinc-950">
      <div className="flex items-start justify-between gap-3 border-b border-zinc-800 px-4 py-3">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-600">
            Human ownership gate
          </p>
          <h3 id="explain-heading" className="mt-1 text-sm font-medium text-zinc-300">
            Line explanation
          </h3>
        </div>
        <span className={`border px-2 py-1 font-mono text-[9px] uppercase tracking-wider ${explainTone(attempt.gates.explain.passed)}`}>
          {attempt.gates.explain.passed === true
            ? "citations passed"
            : attempt.gates.explain.passed === false
              ? "citations failed"
              : "not evaluated"}
        </span>
      </div>

      {!rationale ? (
        <p className="px-4 py-6 text-xs leading-5 text-zinc-500">
          No structured rationale was recorded for this attempt.
        </p>
      ) : selection ? (
        <div className="divide-y divide-zinc-900">
          <div className="px-4 py-4">
            <p className="font-mono text-[10px] text-sky-300">
              {selection.path}:{selection.newLine ?? selection.oldLine}
            </p>
            <pre className="mt-2 overflow-x-auto bg-zinc-900 px-3 py-2 font-mono text-[10px] text-zinc-400">
              {selection.text || "(deleted line)"}
            </pre>
          </div>
          {lineRationale ? (
            <>
              <ExplainField label="Why this changed" value={lineRationale.why} />
              <ExplainField label="Security evidence earned" value={evidenceValue(lineRationale.earns, attempt.raw.harness)} mono />
            </>
          ) : (
            <p className="px-4 py-4 text-xs leading-5 text-amber-300">
              {selection.newLine === null
                ? "This deletion has no candidate-side line; the explanation gate covers added and replaced candidate lines."
                : "No line rationale covers this candidate line."}
            </p>
          )}
          <BehaviourClaims attempt={attempt} />
        </div>
      ) : (
        <div className="px-4 py-5">
          <p className="text-xs leading-5 text-zinc-500">
            Select a highlighted changed line to inspect why it exists and which evidence supports it.
          </p>
          <dl className="mt-4 grid gap-3">
            <Overview label="Vulnerability mechanism" value={rationale.vulnerability_mechanism} />
            <Overview label="Fix mechanism" value={rationale.fix_mechanism} />
          </dl>
        </div>
      )}

      {rationale ? (
        <div className="grid gap-4 border-t border-zinc-800 px-4 py-4 text-xs sm:grid-cols-2">
          <Checklist label="Residual risk" items={rationale.residual_risk} />
          <Checklist label="Reviewer must confirm" items={rationale.reviewer_must_confirm} />
        </div>
      ) : null}
    </section>
  );
}

function findLineRationale(
  rationales: LineRationale[],
  selection: DiffLineSelection,
): LineRationale | null {
  if (selection.newLine === null) return null;
  return (
    rationales.find(
      (item) =>
        normalizePath(item.path) === normalizePath(selection.path) &&
        item.changed_lines.includes(selection.newLine as number),
    ) ?? null
  );
}

function BehaviourClaims({ attempt }: { attempt: AttemptDetail }) {
  const claims = attempt.rationale?.behaviour_preservation ?? [];
  return (
    <div className="px-4 py-4">
      <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-zinc-600">
        Behaviour held by
      </p>
      {claims.length ? (
        <ul className="mt-3 grid gap-3">
          {claims.map((claim) => (
            <li className="border-l border-emerald-500/40 pl-3" key={`${claim.behaviour}-${claim.proven_by}`}>
              <p className="text-xs leading-5 text-zinc-400">{claim.behaviour}</p>
              <p className="mt-1 text-[11px] leading-5 text-zinc-600">{claim.preserved_by}</p>
              <code className="mt-1 block break-all font-mono text-[10px] text-emerald-300">{claim.proven_by}</code>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs text-zinc-600">No behavior-preservation claim was supplied.</p>
      )}
    </div>
  );
}

function ExplainField({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="px-4 py-4">
      <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-zinc-600">{label}</p>
      <p className={`mt-2 text-xs leading-5 text-zinc-400 ${mono ? "break-all font-mono text-[10px]" : ""}`}>
        {value}
      </p>
    </div>
  );
}

function Overview({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-mono text-[9px] uppercase tracking-wider text-zinc-600">{label}</dt>
      <dd className="mt-1 text-xs leading-5 text-zinc-400">{value}</dd>
    </div>
  );
}

function Checklist({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <h4 className="font-mono text-[9px] uppercase tracking-[0.16em] text-zinc-600">{label}</h4>
      {items.length ? (
        <ul className="mt-2 grid gap-2 text-[11px] leading-5 text-zinc-500">
          {items.map((item) => (
            <li className="flex gap-2" key={item}>
              <span className="text-amber-400" aria-hidden="true">—</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[11px] text-zinc-600">None supplied.</p>
      )}
    </div>
  );
}

function evidenceValue(reference: string, rawHarness: string | null): string {
  const index = Number(reference.match(/^security\.payload\[(\d+)]$/)?.[1]);
  if (!Number.isInteger(index) || !rawHarness) return reference;
  try {
    const parsed = JSON.parse(rawHarness) as { payloads?: unknown[] };
    const payload = parsed.payloads?.[index];
    return payload === undefined ? reference : `${reference}\n${JSON.stringify(payload, null, 2)}`;
  } catch {
    return reference;
  }
}

function explainTone(passed: boolean | undefined): string {
  if (passed === true) return "border-emerald-500/40 text-emerald-300";
  if (passed === false) return "border-rose-500/40 text-rose-300";
  return "border-zinc-700 text-zinc-500";
}

function normalizePath(path: string): string {
  return path.replaceAll("\\", "/").replace(/^\.\//, "");
}
