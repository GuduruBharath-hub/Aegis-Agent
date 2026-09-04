import api from './api';

export interface BenchmarkScenario {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  language: string;
  vulnerability_types: string[];
  expected_decision: string;
  expected_attempts: number | null;
}

export interface BenchmarkRun {
  id: number;
  case_id: string;
  job_id: string;
  expected_decision: string;
  actual_decision: string | null;
  attempts_used: number | null;
  duration_ms: number | null;
  correct: boolean | null;
  false_verification: boolean;
  status: 'running' | 'completed';
  run_at: string;
}

export async function getBenchmarkScenarios(): Promise<BenchmarkScenario[]> {
  const { data } = await api.get('/api/benchmarks/scenarios');
  return data;
}

export async function runBenchmark(scenarioId: string): Promise<BenchmarkRun> {
  const { data } = await api.post(`/api/benchmarks/run`, { scenario_id: scenarioId });
  return data;
}

export async function getBenchmarkRuns(): Promise<BenchmarkRun[]> {
  const { data } = await api.get('/api/benchmarks/runs');
  return data;
}

export async function getBenchmarkRun(id: number): Promise<BenchmarkRun> {
  const { data } = await api.get(`/api/benchmarks/runs/${id}`);
  return data;
}
