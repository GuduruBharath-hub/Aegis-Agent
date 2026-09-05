import type { JobEvent } from '@/types/job';
import { toEvent, type ApiEvent } from './jobs';
import { BASE_URL } from './api';

export type EventHandler = (event: JobEvent) => void;
export type ErrorHandler = (error: Event) => void;
export type ConnectionHandler = () => void;

export interface EventSourceOptions {
  onEvent: EventHandler;
  onError?: ErrorHandler;
  onOpen?: ConnectionHandler;
  onClose?: ConnectionHandler;
}

const EVENT_TYPES = [
  'job_created', 'scan_started', 'scan_completed', 'finding_detected',
  'reproduction_started', 'reproduction_confirmed', 'context_built', 'patch_generated',
  'policy_passed', 'policy_failed', 'sandbox_started', 'security_passed',
  'sandbox_completed',
  'security_failed', 'regression_passed', 'regression_failed',
  'post_scan_passed', 'post_scan_failed', 'integrity_passed',
  'integrity_failed', 'explain_passed', 'explain_failed',
  'candidate_rejected', 'verified', 'pr_created', 'escalated',
  'technical_error', 'state_changed',
];

/**
 * Creates an SSE connection to stream job events in real-time.
 * Returns a cleanup function to close the connection.
 */
export function createJobEventStream(
  jobId: string,
  options: EventSourceOptions
): () => void {
  const url = `${BASE_URL}/api/jobs/${jobId}/stream`;
  const eventSource = new EventSource(url);

  eventSource.onopen = () => {
    options.onOpen?.();
  };

  const receive = (e: MessageEvent) => {
    try {
      options.onEvent(toEvent(JSON.parse(e.data) as ApiEvent));
    } catch {
      console.error('[EventStream] Failed to parse event:', e.data);
    }
  };
  eventSource.onmessage = receive;
  EVENT_TYPES.forEach((eventType) => eventSource.addEventListener(eventType, receive as EventListener));

  eventSource.onerror = (e: Event) => {
    options.onError?.(e);
    // Auto-close on error
    eventSource.close();
    options.onClose?.();
  };

  return () => {
    eventSource.close();
    options.onClose?.();
  };
}

/**
 * Parses a raw SSE data string into a JobEvent.
 */
export function parseJobEvent(raw: string): JobEvent | null {
  try {
    return JSON.parse(raw) as JobEvent;
  } catch {
    return null;
  }
}

/**
 * Checks if the browser supports EventSource (SSE).
 */
export function supportsSSE(): boolean {
  return typeof window !== 'undefined' && 'EventSource' in window;
}
