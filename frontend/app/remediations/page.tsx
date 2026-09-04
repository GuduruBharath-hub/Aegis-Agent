'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { getJobs } from '@/lib/jobs';
import { formatRelativeTime, extractRepoName, percentage } from '@/lib/utils';
import type { JobSummary } from '@/types/job';
import { Search, ShieldCheck } from 'lucide-react';

export default function RemediationsPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    getJobs({ page: 1, page_size: 50 })
      .then((res) => setJobs(res.items.filter((j) => j.total_findings > 0)))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = jobs.filter(
    (j) => !search || j.repo_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <Header title="Remediations" subtitle="Active and completed vulnerability remediations" />
      <PageContainer>
        <div style={{ position: 'relative', maxWidth: '400px', marginBottom: '20px' }}>
          <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'rgba(212,175,55,0.3)' }} />
          <input
            type="text"
            placeholder="Search remediations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(212,175,55,0.15)', borderRadius: '8px', padding: '9px 12px 9px 36px', color: '#ffd700', fontSize: '0.875rem', outline: 'none' }}
          />
        </div>

        {loading ? (
          <div className="grid-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{ height: '140px', background: 'rgba(212,175,55,0.03)', borderRadius: '12px', animation: 'pulse-glow 1.5s ease-in-out infinite' }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            variant={search ? 'search' : 'empty'}
            title={search ? 'No remediations match' : 'No remediations yet'}
            description="Remediations appear here when jobs detect and patch vulnerabilities."
          />
        ) : (
          <div className="grid-3">
            {filtered.map((job) => {
              const patchPct = percentage(job.patched_findings, job.total_findings);
              return (
                <Link key={job.id} href={`/remediations/${job.id}`} style={{ textDecoration: 'none' }}>
                  <div
                    style={{
                      background: 'linear-gradient(135deg, rgba(22,22,22,0.97) 0%, rgba(12,12,12,0.99) 100%)',
                      border: '1px solid rgba(212,175,55,0.15)',
                      borderRadius: '12px',
                      padding: '18px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      height: '100%',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(212,175,55,0.1)', border: '1px solid rgba(212,175,55,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <ShieldCheck size={15} color="#d4af37" />
                        </div>
                        <Badge
                          variant={
                            job.status === 'completed' ? 'completed' :
                            job.status === 'running' ? 'running' :
                            job.status === 'failed' ? 'failed' : 'pending'
                          }
                          dot
                        />
                      </div>
                      <span style={{ fontSize: '0.72rem', color: 'rgba(212,175,55,0.3)' }}>
                        {formatRelativeTime(job.created_at)}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ffd700', marginBottom: '6px', fontFamily: 'JetBrains Mono, monospace' }}>
                      {extractRepoName(job.repo_name)}
                    </h3>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'rgba(212,175,55,0.4)', marginBottom: '10px' }}>
                      <span>{job.total_findings} findings</span>
                      <span style={{ color: patchPct >= 80 ? '#a8e063' : '#ffd700', fontWeight: 600 }}>{patchPct}% patched</span>
                    </div>

                    <div style={{ height: '4px', background: 'rgba(212,175,55,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${patchPct}%`, background: patchPct >= 80 ? '#a8e063' : 'linear-gradient(90deg, #d4af37, #ffd700)', borderRadius: '2px', transition: 'width 0.6s ease' }} />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </PageContainer>
    </>
  );
}
