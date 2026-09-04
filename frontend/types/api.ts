// Core API response types that mirror backend schemas.py

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  code?: string;
  status_code: number;
}

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type FindingStatus = 'open' | 'in_remediation' | 'patched' | 'verified' | 'wont_fix';
export type RemediationStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'needs_review';
export type AttemptStatus = 'running' | 'success' | 'failed' | 'timeout';
export type GateStatus = 'pending' | 'passed' | 'failed' | 'skipped';
export type ValidationStatus = 'pending' | 'passed' | 'failed';
