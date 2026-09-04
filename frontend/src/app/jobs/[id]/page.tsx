interface JobPageProps {
  params: Promise<{ id: string }>;
}

export default async function JobPage({ params }: JobPageProps) {
  const { id } = await params;
  return (
    <main className="min-h-screen bg-zinc-950 p-8 text-zinc-100">
      <p className="font-mono text-xs uppercase tracking-widest text-emerald-400">
        Live remediation job
      </p>
      <h1 className="mt-3 font-mono text-2xl">{id}</h1>
      <p className="mt-6 text-zinc-400">
        Dashboard components will attach to the history-first event stream here.
      </p>
    </main>
  );
}
