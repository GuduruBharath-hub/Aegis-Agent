import type { FinalDecision } from "@/lib/api";

interface VerdictBannerProps {
  decision: FinalDecision | null;
  reason: string | null;
}

export function VerdictBanner({ decision, reason }: VerdictBannerProps) {
  const presentation = presentationFor(decision);
  return (
    <section
      aria-labelledby="verdict-heading"
      className={`border px-5 py-6 md:px-7 ${presentation.colors}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.24em] opacity-60">
            Server final decision
          </p>
          <h2 id="verdict-heading" className="mt-2 font-mono text-2xl font-semibold tracking-[0.08em]">
            {presentation.label}
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 opacity-80">
            {reason ?? presentation.description}
          </p>
        </div>
        <span className="border border-current/30 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.18em]">
          {decision === null ? "pending" : "authoritative"}
        </span>
      </div>
    </section>
  );
}

function presentationFor(decision: FinalDecision | null) {
  if (decision === "verified") {
    return {
      label: "VERIFIED",
      description: "All configured gates passed; the candidate earned delivery.",
      colors: "border-emerald-500/50 bg-emerald-500/10 text-emerald-100",
    };
  }
  if (decision === "escalated") {
    return {
      label: "ESCALATED",
      description: "No candidate earned delivery; human review is required.",
      colors: "border-amber-500/50 bg-amber-500/10 text-amber-100",
    };
  }
  if (decision === "policy_rejected") {
    return {
      label: "POLICY REJECTED",
      description: "Static controls refused the candidate; the repository is unchanged.",
      colors: "border-amber-500/50 bg-amber-500/10 text-amber-100",
    };
  }
  if (decision === "failed") {
    return {
      label: "FAILED",
      description: "The run ended with a technical failure; nothing was delivered.",
      colors: "border-rose-500/50 bg-rose-500/10 text-rose-100",
    };
  }
  return {
    label: "AWAITING VERDICT",
    description: "No final decision has been recorded by the server.",
    colors: "border-zinc-700 bg-zinc-900 text-zinc-300",
  };
}
