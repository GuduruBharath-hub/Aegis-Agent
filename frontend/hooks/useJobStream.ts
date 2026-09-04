'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { createJobEventStream, supportsSSE } from '@/lib/events';
import type { JobEvent } from '@/types/job';

type StreamStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'unsupported';

interface UseJobStreamResult {
  events: JobEvent[];
  status: StreamStatus;
  connect: () => void;
  disconnect: () => void;
  clearEvents: () => void;
}

export function useJobStream(jobId: string, maxEvents = 500): UseJobStreamResult {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [status, setStatus] = useState<StreamStatus>('disconnected');
  const cleanupRef = useRef<(() => void) | null>(null);

  const disconnect = useCallback(() => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  const connect = useCallback(() => {
    if (!supportsSSE()) {
      setStatus('unsupported');
      return;
    }
    if (!jobId) return;

    disconnect();
    setStatus('connecting');

    const cleanup = createJobEventStream(jobId, {
      onOpen: () => setStatus('connected'),
      onEvent: (event: JobEvent) => {
        setEvents((prev) => {
          const updated = [...prev, event];
          return updated.length > maxEvents ? updated.slice(-maxEvents) : updated;
        });
      },
      onError: () => setStatus('error'),
      onClose: () => setStatus('disconnected'),
    });

    cleanupRef.current = cleanup;
  }, [jobId, maxEvents, disconnect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  // Auto-connect when jobId changes
  useEffect(() => {
    if (jobId) connect();
    return disconnect;
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  return { events, status, connect, disconnect, clearEvents };
}
