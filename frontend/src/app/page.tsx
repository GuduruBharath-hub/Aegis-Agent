export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-6 text-zinc-100">
      <main className="w-full max-w-3xl border border-zinc-800 bg-zinc-900 p-10">
        <p className="font-mono text-xs uppercase tracking-[0.24em] text-emerald-400">
          AegisAgent control plane
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight">
          Evidence earns delivery.
        </h1>
        <p className="mt-4 max-w-2xl text-zinc-400">
          The API data layer is connected. The live remediation dashboard is the
          next build step.
        </p>
      </main>
    </div>
  );
}
