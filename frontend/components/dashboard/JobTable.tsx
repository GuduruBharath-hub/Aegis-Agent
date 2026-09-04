'use client';

import React from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/Badge';
import { extractRepoName, formatRelativeTime } from '@/lib/utils';
import type { JobSummary } from '@/types/job';
import type { JobStatus } from '@/types/api';

interface JobTableProps {
  jobs: JobSummary[];
  loading?: boolean;
}

const columns = [
  { key: 'repo', label: 'Repository', width: '2fr' },
  { key: 'status', label: 'Status', width: '1fr' },
  { key: 'findings', label: 'Findings', width: '1fr' },
  { key: 'patched', label: 'Patched', width: '1fr' },
  { key: 'time', label: 'Time', width: '1fr' },
];

const statusVariantMap: Record<JobStatus, string> = {
  pending: 'pending',
  running: 'running',
  completed: 'completed',
  failed: 'failed',
  cancelled: 'cancelled',
};

export const JobTable: React.FC<JobTableProps> = ({ jobs, loading = false }) => {
  return (
    <div
      style={{
        background: `
          linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%),
          linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.98) 100%)
        `,
        border: '1px solid rgba(251,191,36,0.1)',
        borderRadius: '14px',
        overflow: 'hidden',
        boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 32px rgba(0,0,0,0.5)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '18px 22px',
          borderBottom: '1px solid rgba(251,191,36,0.08)',
        }}
      >
        <h3
          style={{
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'rgba(148,163,184,0.7)',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
          }}
        >
          Recent Jobs
        </h3>
        <Link
          href="/jobs"
          style={{
            fontSize: '0.78rem',
            color: 'rgba(251,191,36,0.5)',
            textDecoration: 'none',
            fontWeight: 500,
            transition: 'color 0.15s ease',
          }}
        >
          View All →
        </Link>
      </div>

      {/* Column headers */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: columns.map((c) => c.width).join(' '),
          padding: '10px 22px',
          borderBottom: '1px solid rgba(251,191,36,0.05)',
        }}
      >
        {columns.map((col) => (
          <div
            key={col.key}
            style={{
              fontSize: '0.65rem',
              fontWeight: 700,
              color: 'rgba(148,163,184,0.5)',
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
            }}
          >
            {col.label}
          </div>
        ))}
      </div>

      {/* Rows */}
      {loading
        ? Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: columns.map((c) => c.width).join(' '),
                padding: '14px 22px',
                borderBottom: '1px solid rgba(251,191,36,0.03)',
                gap: '8px',
              }}
            >
              {columns.map((_, j) => (
                <div
                  key={j}
                  style={{
                    height: '16px',
                    borderRadius: '6px',
                    background: 'linear-gradient(90deg, rgba(251,191,36,0.04) 0%, rgba(251,191,36,0.01) 50%, rgba(251,191,36,0.04) 100%)',
                    backgroundSize: '200% 100%',
                    animation: 'shimmer 1.5s ease-in-out infinite',
                  }}
                />
              ))}
            </div>
          ))
        : jobs.slice(0, 8).map((job) => (
            <Link
              key={job.id}
              href={`/jobs/${job.id}`}
              style={{
                display: 'grid',
                gridTemplateColumns: columns.map((c) => c.width).join(' '),
                padding: '14px 22px',
                borderBottom: '1px solid rgba(251,191,36,0.03)',
                textDecoration: 'none',
                alignItems: 'center',
                transition: 'background 0.15s ease',
              }}
            >
              <div>
                <div
                  style={{
                    fontWeight: 500,
                    color: '#F8FAFC',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '0.82rem',
                  }}
                >
                  {extractRepoName(job.repo_name)}
                </div>
              </div>
              <div>
                <Badge variant={statusVariantMap[job.status]} dot />
              </div>
              <div>
                <span style={{ fontSize: '0.85rem', color: 'rgba(248,250,252,0.7)' }}>{job.total_findings}</span>
              </div>
              <div>
                <span
                  style={{
                    fontSize: '0.85rem',
                    color: job.patched_findings > 0 ? '#34D399' : 'rgba(148,163,184,0.3)',
                    fontWeight: job.patched_findings > 0 ? 600 : 400,
                  }}
                >
                  {job.patched_findings}
                </span>
              </div>
              <div>
                <span style={{ fontSize: '0.78rem', color: 'rgba(148,163,184,0.5)' }}>
                  {formatRelativeTime(job.created_at)}
                </span>
              </div>
            </Link>
          ))}
    </div>
  );
};

export default JobTable;
