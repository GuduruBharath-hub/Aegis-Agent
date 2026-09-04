import api from './api';
import type { Job, JobSummary, JobEvent, JobAttempt, StartJobRequest } from '@/types/job';
import type { PaginatedResponse } from '@/types/api';

export async function getJobs(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
}): Promise<PaginatedResponse<JobSummary>> {
  const { data } = await api.get('/api/jobs', { params });
  return data;
}

export async function getJob(id: string): Promise<Job> {
  const { data } = await api.get(`/api/jobs/${id}`);
  return data;
}

export async function startJob(request: StartJobRequest): Promise<Job> {
  const { data } = await api.post('/api/jobs', request);
  return data;
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
  const { data } = await api.get(`/api/jobs/${id}/events`, { params });
  return data;
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
