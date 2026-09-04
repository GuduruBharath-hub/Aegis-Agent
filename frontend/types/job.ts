import type { JobStatus, AttemptStatus } from './api';

export interface Job {
  id: string;
  repo_url: string;
  repo_name: string;
  branch: string;
  status: JobStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  total_findings: number;
  patched_findings: number;
  failed_findings: number;
  current_attempt?: number;
  max_attempts: number;
  error_message?: string;
  metadata?: Record<string, unknown>;
}

export interface JobSummary {
  id: string;
  repo_name: string;
  status: JobStatus;
  created_at: string;
  completed_at?: string;
  total_findings: number;
  patched_findings: number;
}

export interface JobEvent {
  id: string;
  job_id: string;
  timestamp: string;
  event_type: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  data?: Record<string, unknown>;
  attempt?: number;
}

export interface JobAttempt {
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
}

export interface AttemptStep {
  id: string;
  name: string;
  display_name?: string;
  order?: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  message?: string;
}

export interface StartJobRequest {
  repo_url: string;
  branch?: string;
  max_attempts?: number;
  finding_ids?: string[];
}
