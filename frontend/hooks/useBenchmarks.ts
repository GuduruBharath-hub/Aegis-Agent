'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getBenchmarkScenarios,
  getBenchmarkRuns,
  runBenchmark,
  type BenchmarkScenario,
  type BenchmarkRun,
} from '@/lib/benchmarks';

interface UseBenchmarksResult {
  scenarios: BenchmarkScenario[];
  runs: BenchmarkRun[];
  loading: boolean;
  running: string | null;
  error: string | null;
  triggerRun: (scenarioId: string) => Promise<BenchmarkRun | null>;
  refetch: () => Promise<void>;
}

export function useBenchmarks(): UseBenchmarksResult {
  const [scenarios, setScenarios] = useState<BenchmarkScenario[]>([]);
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [scenariosData, runsData] = await Promise.all([
        getBenchmarkScenarios(),
        getBenchmarkRuns(),
      ]);
      setScenarios(scenariosData);
      setRuns(runsData);
      setError(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch benchmarks';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerRun = useCallback(async (scenarioId: string): Promise<BenchmarkRun | null> => {
    setRunning(scenarioId);
    try {
      const run = await runBenchmark(scenarioId);
      setRuns((prev) => [run, ...prev]);
      return run;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start benchmark';
      setError(message);
      return null;
    } finally {
      setRunning(null);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!runs.some((run) => run.status === 'running')) return;
    const timer = window.setInterval(fetchData, 2000);
    return () => window.clearInterval(timer);
  }, [fetchData, runs]);

  return { scenarios, runs, loading, running, error, triggerRun, refetch: fetchData };
}
