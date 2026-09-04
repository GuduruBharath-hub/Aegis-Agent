const GUARDRAILS = [
  "Read the hidden security oracle",
  "Modify protected tests, policy, CI, or sandbox code",
  "Access credentials from the candidate workspace",
  "Reach the network from inside the sandbox",
  "Extend the configured retry budget",
  "Mark its own patch verified",
  "Merge or deploy any pull request",
] as const;

export function GuardrailList() {
  return (
    <section aria-labelledby="guardrails-heading" className="border border-zinc-800 bg-zinc-950 px-5 py-6 md:px-7">
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.24em] text-zinc-600">
            Structural limits
          </p>
          <h2 id="guardrails-heading" className="mt-2 text-lg font-medium text-zinc-200">
            What the AI cannot do
          </h2>
          <p className="mt-3 text-xs leading-5 text-zinc-500">
            These restrictions are enforced outside the model and remain active for every attempt.
          </p>
        </div>
        <ol className="grid gap-px border border-zinc-800 bg-zinc-800 sm:grid-cols-2">
          {GUARDRAILS.map((guardrail, index) => (
            <li className="flex min-h-16 items-center gap-3 bg-zinc-950 px-4 py-3 sm:last:col-span-2" key={guardrail}>
              <span className="font-mono text-[10px] text-emerald-400" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="text-xs leading-5 text-zinc-400">{guardrail}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
