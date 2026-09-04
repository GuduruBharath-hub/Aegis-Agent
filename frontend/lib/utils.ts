import type { Severity, JobStatus, FindingStatus, RemediationStatus } from '@/types/api';

/**
 * Merge class names, filtering falsy values.
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

/**
 * Format an ISO date string to a human-readable format.
 */
export function formatDate(iso: string, opts?: Intl.DateTimeFormatOptions): string {
  const date = new Date(iso);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...opts,
  });
}

/**
 * Format a relative time (e.g. "5 minutes ago").
 */
export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

/**
 * Format a duration in seconds to a human-readable string.
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 60) return `${mins}m ${secs}s`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
}

/**
 * Returns CSS color variable name for severity levels.
 */
export function severityColor(severity: Severity): string {
  const map: Record<Severity, string> = {
    critical: '#ff4d4f',
    high: '#ff7a45',
    medium: '#ffa940',
    low: '#52c41a',
    info: '#1890ff',
  };
  return map[severity] ?? '#8c8c8c';
}

/**
 * Returns CSS color for job status.
 */
export function jobStatusColor(status: JobStatus): string {
  const map: Record<JobStatus, string> = {
    pending: '#8c8c8c',
    running: '#1890ff',
    completed: '#52c41a',
    failed: '#ff4d4f',
    cancelled: '#faad14',
  };
  return map[status] ?? '#8c8c8c';
}

/**
 * Returns CSS color for finding status.
 */
export function findingStatusColor(status: FindingStatus): string {
  const map: Record<FindingStatus, string> = {
    open: '#ff4d4f',
    in_remediation: '#1890ff',
    patched: '#52c41a',
    verified: '#13c2c2',
    wont_fix: '#8c8c8c',
  };
  return map[status] ?? '#8c8c8c';
}

/**
 * Returns CSS color for remediation status.
 */
export function remediationStatusColor(status: RemediationStatus): string {
  const map: Record<RemediationStatus, string> = {
    pending: '#8c8c8c',
    in_progress: '#1890ff',
    completed: '#52c41a',
    failed: '#ff4d4f',
    needs_review: '#faad14',
  };
  return map[status] ?? '#8c8c8c';
}

/**
 * Truncates text to a maximum length with ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * Extract repository name from a URL.
 */
export function extractRepoName(url: string): string {
  try {
    const parts = url.replace(/\.git$/, '').split('/');
    return parts.slice(-2).join('/');
  } catch {
    return url;
  }
}

/**
 * Calculate percentage safely.
 */
export function percentage(value: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((value / total) * 100);
}

/**
 * Capitalize the first letter of a string.
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
