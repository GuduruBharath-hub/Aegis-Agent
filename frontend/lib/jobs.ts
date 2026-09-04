import api from './api';
import type { Job, JobSummary, JobEvent, JobAttempt, StartJobRequest } from '@/types/job';
import type { PaginatedResponse } from '@/types/api';

interface ApiFinding {
  id: string;
}

interface ApiJob {
  id: string;
  repository: string;
  repository_url: string;
  base_sha: string;
  state: string;
  current_attempt: number;
  max_attempts: number;
  sandbox_tier: string | null;
  final_decision: string | null;
  final_reason: string | null;
  branch_name: string | null;
  pr_url: string | null;
  repository_changed: boolean;
  finding: ApiFinding | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

interface ApiEvent {
  seq: number;
  job_id: string;
  ts: string;
  type: string;
  severity: string;
  message: string | null;
  title: string;
  data: Record<string, unknown> | null;
  attempt: number | null;
}

export async function getJobs(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
}): Promise<PaginatedResponse<JobSummary>> {
  const { data } = await api.get<ApiJob[]>('/api/jobs');
  let items = data.map(toSummary);
  if (params?.status) items = items.filter((job) => job.status === params.status);
  if (params?.search) {
    const search = params.search.toLowerCase();
    items = items.filter((job) => job.repo_name.toLowerCase().includes(search));
  }
  const page = params?.page ?? 1;
  const pageSize = (params?.page_size ?? items.length) || 1;
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    page_size: pageSize,
    pages: Math.max(1, Math.ceil(items.length / pageSize)),
  };
}

export async function getJob(id: string): Promise<Job> {
  const { data } = await api.get<ApiJob>(`/api/jobs/${id}`);
  return toJob(data);
}

export async function startJob(request: StartJobRequest): Promise<Job> {
  const { data } = await api.post<{ job_id: string }>('/api/jobs', {
    repository_url: request.repo_url,
    commit_sha: request.branch ?? 'HEAD',
    mode: 'live',
  });
  return getJob(data.job_id);
}

export async function cancelJob(id: string): Promise<void> {
  await api.post(`/api/jobs/${id}/cancel`);
}

export async function retryJob(id: string): Promise<Job> {
  const { data } = await api.post(`/api/jobs/${id}/retry`);
  return data;
}

export async function getJobEvents(
  id: string,
  params?: { page?: number; page_size?: number; level?: string }
): Promise<PaginatedResponse<JobEvent>> {
  const { data } = await api.get<ApiEvent[]>(`/api/jobs/${id}/events`);
  const items = data.map(toEvent);
  const page = params?.page ?? 1;
  const pageSize = (params?.page_size ?? items.length) || 1;
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    page_size: pageSize,
    pages: Math.max(1, Math.ceil(items.length / pageSize)),
  };
}

export async function getJobAttempts(id: string): Promise<JobAttempt[]> {
  const { data } = await api.get(`/api/jobs/${id}/attempts`);
  return data;
}

export async function getJobAudit(id: string): Promise<{ audit_id: string }> {
  const { data } = await api.get(`/api/jobs/${id}/audit`);
  return data;
}

export async function deleteJob(id: string): Promise<void> {
  await api.delete(`/api/jobs/${id}`);
}

function displayStatus(job: ApiJob): Job['status'] {
  if (job.state === 'received') return 'pending';
  if (job.state === 'failed') return 'failed';
  if (['completed', 'escalated', 'policy_rejected'].includes(job.state)) return 'completed';
  return 'running';
}

function toJob(job: ApiJob): Job {
  const findingCount = job.finding ? 1 : 0;
  return {
    id: job.id,
    repo_url: job.repository_url,
    repo_name: job.repository,
    branch: job.branch_name ?? job.base_sha.slice(0, 12),
    status: displayStatus(job),
    state: job.state,
    final_decision: job.final_decision,
    final_reason: job.final_reason,
    repository_changed: job.repository_changed,
    pr_url: job.pr_url,
    sandbox_tier: job.sandbox_tier,
    created_at: job.created_at,
    completed_at: job.completed_at ?? undefined,
    total_findings: findingCount,
    patched_findings: job.final_decision === 'verified' ? findingCount : 0,
    failed_findings: job.final_decision && job.final_decision !== 'verified' ? findingCount : 0,
    current_attempt: job.current_attempt,
    max_attempts: job.max_attempts,
    error_message: job.state === 'failed' ? job.final_reason ?? undefined : undefined,
  };
}

function toSummary(job: ApiJob): JobSummary {
  const mapped = toJob(job);
  return {
    id: mapped.id,
    repo_name: mapped.repo_name,
    status: mapped.status,
    created_at: mapped.created_at,
    completed_at: mapped.completed_at,
    total_findings: mapped.total_findings,
    patched_findings: mapped.patched_findings,
    final_decision: mapped.final_decision,
  };
}

export function toEvent(event: ApiEvent): JobEvent {
  return {
    id: String(event.seq),
    job_id: event.job_id,
    timestamp: event.ts,
    event_type: event.type,
    level: event.severity === 'critical' ? 'error' : event.severity === 'warning' ? 'warning' : 'info',
    message: event.message ?? event.title,
    data: event.data ?? undefined,
    attempt: event.attempt ?? undefined,
  };
}
