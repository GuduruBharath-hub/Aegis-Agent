'use client';

import { useState, useEffect, useCallback } from 'react';
import { getJobEvents } from '@/lib/jobs';
import type { JobEvent } from '@/types/job';

interface UseJobEventsResult {
  events: JobEvent[];
  loading: boolean;
  error: string | null;
  total: number;
  page: number;
  totalPages: number;
  setPage: (page: number) => void;
  refetch: () => Promise<void>;
}

export function useJobEvents(
  jobId: string,
  options?: { pageSize?: number; level?: string; autoRefresh?: boolean }
): UseJobEventsResult {
  const { pageSize = 50, level, autoRefresh = false } = options ?? {};
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const fetchEvents = useCallback(async () => {
    if (!jobId) return;
    try {
      const result = await getJobEvents(jobId, { page, page_size: pageSize, level });
      setEvents(result.items);
      setTotal(result.total);
      setTotalPages(result.pages);
      setError(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch events';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [jobId, page, pageSize, level]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchEvents, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchEvents]);

  return { events, loading, error, total, page, totalPages, setPage, refetch: fetchEvents };
}
