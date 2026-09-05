'use client';

import { useState, useEffect, useCallback } from 'react';
import { getJob } from '@/lib/jobs';
import type { Job } from '@/types/job';

interface UseJobResult {
  job: Job | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useJob(id: string, pollInterval = 5000): UseJobResult {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJob = useCallback(async () => {
    try {
      const data = await getJob(id);
      setJob(data);
      setError(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch job';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  const jobStatus = job?.status;

  useEffect(() => {
    if (!id) return;
    // The effect synchronizes local state with the job API.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchJob();

    // Only poll if job is in an active state
    const shouldPoll = () => {
      const activeStatuses = ['pending', 'running'];
      return jobStatus ? activeStatuses.includes(jobStatus) : true;
    };

    if (!pollInterval || !shouldPoll()) return;

    const interval = setInterval(() => {
      fetchJob();
    }, pollInterval);

    return () => clearInterval(interval);
  }, [id, fetchJob, pollInterval, jobStatus]);

  return { job, loading, error, refetch: fetchJob };
}
