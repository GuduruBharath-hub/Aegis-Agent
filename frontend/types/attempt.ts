import type { AttemptStatus } from './api';
import type { Finding } from './finding';

export interface Attempt {
  id: string;
  job_id: string;
  attempt_number: number;
  status: AttemptStatus;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  findings_processed: number;
  findings_patched: number;
  findings_failed: number;
  error_message?: string;
  steps: AttemptStep[];
  findings?: Finding[];
}

export interface AttemptStep {
  id: string;
  attempt_id: string;
  name: string;
  display_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  message?: string;
  output?: string;
  order: number;
}

export interface AttemptSummary {
  id: string;
  attempt_number: number;
  status: AttemptStatus;
  started_at: string;
  completed_at?: string;
  findings_patched: number;
  findings_failed: number;
}
