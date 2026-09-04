import api from './api';

export interface BenchmarkScenario {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  language: string;
  vulnerability_types: string[];
  expected_findings: number;
  repo_url?: string;
  tags: string[];
}

export interface BenchmarkRun {
  id: string;
  scenario_id: string;
  scenario_name: string;
  job_id?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  score?: number;
  findings_detected: number;
  findings_expected: number;
  detection_rate: number;
  patch_success_rate: number;
  false_positive_rate: number;
  metrics?: Record<string, number>;
}

export async function getBenchmarkScenarios(): Promise<BenchmarkScenario[]> {
  const { data } = await api.get('/api/benchmarks/scenarios');
  return data;
}

export async function getBenchmarkScenario(id: string): Promise<BenchmarkScenario> {
  const { data } = await api.get(`/api/benchmarks/scenarios/${id}`);
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

export async function getBenchmarkRun(id: string): Promise<BenchmarkRun> {
  const { data } = await api.get(`/api/benchmarks/runs/${id}`);
  return data;
}
