import type { JobEvent } from '@/types/job';
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

  eventSource.onmessage = (e: MessageEvent) => {
    try {
      const event: JobEvent = JSON.parse(e.data);
      options.onEvent(event);
    } catch {
      console.error('[EventStream] Failed to parse event:', e.data);
    }
  };

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
