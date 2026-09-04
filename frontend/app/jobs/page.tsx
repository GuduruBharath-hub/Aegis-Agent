'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { JobStatusBadge } from '@/components/jobs/JobStatusBadge';
import { StartJobForm } from '@/components/jobs/StartJobForm';
import { Modal } from '@/components/ui/Modal';
import { EmptyState } from '@/components/ui/EmptyState';
import { getJobs } from '@/lib/jobs';
import { formatRelativeTime, extractRepoName } from '@/lib/utils';
import type { JobSummary, Job } from '@/types/job';
import { Plus, Search, RefreshCw, GitBranch } from 'lucide-react';
import { useRouter } from 'next/navigation';

type FilterStatus = 'all' | 'running' | 'completed' | 'failed' | 'pending' | 'cancelled';

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [search, setSearch] = useState('');
  const [showStartJob, setShowStartJob] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await getJobs({ page: 1, page_size: 50, status: filter === 'all' ? undefined : filter });
      setJobs(res.items);
    } catch {
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchJobs(); }, [filter]);

  const filtered = jobs.filter((j) =>
    !search || j.repo_name.toLowerCase().includes(search.toLowerCase())
  );

  const filterBtns: { label: string; value: FilterStatus }[] = [
    { label: 'All', value: 'all' },
    { label: 'Running', value: 'running' },
    { label: 'Completed', value: 'completed' },
    { label: 'Failed', value: 'failed' },
    { label: 'Pending', value: 'pending' },
  ];

  return (
    <>
      <Header
        title="Jobs"
        subtitle="All remediation jobs"
        actions={
          <>
            <button
              onClick={fetchJobs}
              style={{ background: 'transparent', border: '1px solid rgba(148,163,184,0.15)', borderRadius: '10px', color: 'rgba(148,163,184,0.5)', cursor: 'pointer', padding: '8px', display: 'flex', alignItems: 'center', transition: 'all 0.15s ease' }}
            >
              <RefreshCw size={15} />
            </button>
            <button
              onClick={() => setShowStartJob(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 20px', background: 'linear-gradient(135deg, rgba(251,191,36,0.18) 0%, rgba(180,83,9,0.1) 100%)', border: '1px solid rgba(251,191,36,0.4)', borderRadius: '10px', color: '#FDE68A', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, boxShadow: '0 0 20px rgba(251,191,36,0.12), 0 0 40px rgba(251,191,36,0.04)', transition: 'all 0.2s ease' }}
            >
              <Plus size={15} /> New Job
            </button>
          </>
        }
      />

      <PageContainer>
        {/* Filters */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
            <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'rgba(148,163,184,0.4)' }} />
            <input
              type="text"
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: '100%', background: 'rgba(2,6,23,0.6)', border: '1px solid rgba(251,191,36,0.1)', borderRadius: '10px', padding: '10px 12px 10px 36px', color: '#F8FAFC', fontSize: '0.875rem', outline: 'none', transition: 'border-color 0.2s ease' }}
            />
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            {filterBtns.map(({ label, value }) => (
              <button
                key={value}
                onClick={() => setFilter(value)}
                style={{
                  padding: '8px 16px',
                  background: filter === value
                    ? 'linear-gradient(135deg, rgba(251,191,36,0.12) 0%, rgba(251,191,36,0.04) 100%)'
                    : 'transparent',
                  border: filter === value ? '1px solid rgba(251,191,36,0.25)' : '1px solid rgba(148,163,184,0.1)',
                  borderRadius: '10px',
                  color: filter === value ? '#FDE68A' : 'rgba(148,163,184,0.5)',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  fontWeight: filter === value ? 600 : 400,
                  transition: 'all 0.2s ease',
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div
          style={{
            background: `linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%), linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.98) 100%)`,
            border: '1px solid rgba(251,191,36,0.1)',
            borderRadius: '14px',
            overflow: 'hidden',
            boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 32px rgba(0,0,0,0.5)',
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 1fr', padding: '10px 22px', borderBottom: '1px solid rgba(251,191,36,0.06)' }}>
            {['Repository', 'Status', 'Branch', 'Findings', 'Patched', 'Created'].map((col) => (
              <div key={col} style={{ fontSize: '0.65rem', fontWeight: 700, color: 'rgba(148,163,184,0.5)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>{col}</div>
            ))}
          </div>

          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 1fr', padding: '14px 22px', borderBottom: '1px solid rgba(251,191,36,0.03)', gap: '8px' }}>
                {Array.from({ length: 6 }).map((_, j) => (
                  <div key={j} style={{ height: '16px', borderRadius: '6px', background: 'linear-gradient(90deg, rgba(251,191,36,0.04) 0%, rgba(251,191,36,0.01) 50%, rgba(251,191,36,0.04) 100%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s ease-in-out infinite' }} />
                ))}
              </div>
            ))
          ) : filtered.length === 0 ? (
            <EmptyState variant={search ? 'search' : 'empty'} title={search ? 'No matching jobs' : 'No jobs yet'} description={search ? 'Try clearing the search filter.' : 'Start a new remediation job to see it here.'} />
          ) : (
            filtered.map((job) => (
              <Link
                key={job.id}
                href={`/jobs/${job.id}`}
                style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 1fr', padding: '14px 22px', borderBottom: '1px solid rgba(251,191,36,0.03)', textDecoration: 'none', alignItems: 'center', transition: 'background 0.15s ease' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <GitBranch size={13} color="rgba(148,163,184,0.35)" />
                  <span style={{ fontSize: '0.85rem', color: '#F8FAFC', fontFamily: 'JetBrains Mono, monospace', fontWeight: 500 }}>{extractRepoName(job.repo_name)}</span>
                </div>
                <JobStatusBadge status={job.status} />
                <span style={{ fontSize: '0.78rem', color: 'rgba(148,163,184,0.45)', fontFamily: 'JetBrains Mono, monospace' }}>main</span>
                <span style={{ fontSize: '0.875rem', color: 'rgba(248,250,252,0.7)' }}>{job.total_findings}</span>
                <span style={{ fontSize: '0.875rem', color: job.patched_findings > 0 ? '#34D399' : 'rgba(148,163,184,0.3)', fontWeight: job.patched_findings > 0 ? 600 : 400 }}>{job.patched_findings}</span>
                <span style={{ fontSize: '0.8rem', color: 'rgba(148,163,184,0.45)' }}>{formatRelativeTime(job.created_at)}</span>
              </Link>
            ))
          )}
        </div>
      </PageContainer>

      <Modal open={showStartJob} onClose={() => setShowStartJob(false)} title="Start New Remediation Job">
        <StartJobForm onJobStarted={(job) => { setShowStartJob(false); router.push(`/jobs/${job.id}`); }} onCancel={() => setShowStartJob(false)} />
      </Modal>
    </>
  );
}
