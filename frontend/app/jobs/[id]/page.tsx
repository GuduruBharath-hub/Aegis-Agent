'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { JobStatusBadge } from '@/components/jobs/JobStatusBadge';
import { JobEvents } from '@/components/jobs/JobEvents';
import { AttemptCard } from '@/components/jobs/AttemptCard';
import { FinalDecision } from '@/components/remediation/FinalDecision';
import { Progress } from '@/components/ui/Progress';
import { EmptyState } from '@/components/ui/EmptyState';
import { useJob } from '@/hooks/useJob';
import { useJobStream } from '@/hooks/useJobStream';
import { useJobEvents } from '@/hooks/useJobEvents';
import { cancelJob } from '@/lib/jobs';
import { formatDate, formatDuration, percentage, extractRepoName } from '@/lib/utils';
import {
  ArrowLeft,
  GitBranch,
  Clock,
  Wifi,
  WifiOff,
  StopCircle,
  FileText,
  List,
  Layers,
} from 'lucide-react';
import Link from 'next/link';

type TabId = 'stream' | 'events' | 'attempts';

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const [activeTab, setActiveTab] = useState<TabId>('stream');
  const [cancelling, setCancelling] = useState(false);

  const { job, loading, error } = useJob(jobId);
  const { events: streamEvents, status: streamStatus } = useJobStream(jobId);
  const { events: logEvents, loading: eventsLoading } = useJobEvents(jobId, { pageSize: 100, autoRefresh: job?.status === 'running' });

  const handleCancel = async () => {
    setCancelling(true);
    try { await cancelJob(jobId); } finally { setCancelling(false); }
  };

  const patchRate = job ? percentage(job.patched_findings, job.total_findings) : 0;
  const isActive = job?.status === 'running' || job?.status === 'pending';

  const tabStyle = (id: TabId): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    background: activeTab === id ? 'rgba(212,175,55,0.1)' : 'transparent',
    border: activeTab === id ? '1px solid rgba(212,175,55,0.3)' : '1px solid transparent',
    borderRadius: '8px',
    color: activeTab === id ? '#ffd700' : 'rgba(212,175,55,0.45)',
    cursor: 'pointer',
    fontSize: '0.83rem',
    fontWeight: activeTab === id ? 600 : 400,
    transition: 'all 0.15s ease',
  });

  if (loading) {
    return (
      <>
        <Header title="Job Details" />
        <PageContainer>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} style={{ height: '80px', background: 'rgba(212,175,55,0.04)', borderRadius: '10px', animation: 'pulse-glow 1.5s ease-in-out infinite' }} />
            ))}
          </div>
        </PageContainer>
      </>
    );
  }

  if (error || !job) {
    return (
      <>
        <Header title="Job Not Found" />
        <PageContainer>
          <EmptyState variant="error" title="Job not found" description={error ?? 'This job does not exist.'} />
        </PageContainer>
      </>
    );
  }

  return (
    <>
      <Header
        title={extractRepoName(job.repo_name)}
        subtitle={`Job ${job.id.slice(0, 8)}...`}
        runMode={job.mode}
        actions={
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '5px 10px', background: streamStatus === 'connected' ? 'rgba(168,224,99,0.06)' : 'rgba(212,175,55,0.04)', border: `1px solid ${streamStatus === 'connected' ? 'rgba(168,224,99,0.2)' : 'rgba(212,175,55,0.1)'}`, borderRadius: '16px' }}>
              {streamStatus === 'connected' ? <Wifi size={12} color="#a8e063" /> : <WifiOff size={12} color="rgba(212,175,55,0.35)" />}
              <span style={{ fontSize: '0.72rem', color: streamStatus === 'connected' ? '#a8e063' : 'rgba(212,175,55,0.35)', fontWeight: 500 }}>
                {streamStatus === 'connected' ? (job.mode === 'replay' ? 'Recorded stream' : 'Live') : streamStatus}
              </span>
            </div>

            {isActive && (
              <button
                onClick={handleCancel}
                disabled={cancelling}
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px', background: 'rgba(255,69,69,0.08)', border: '1px solid rgba(255,69,69,0.25)', borderRadius: '8px', color: '#ff6060', cursor: 'pointer', fontSize: '0.83rem', fontWeight: 600, opacity: cancelling ? 0.6 : 1 }}
              >
                <StopCircle size={13} />
                {cancelling ? 'Cancelling...' : 'Cancel'}
              </button>
            )}
          </div>
        }
      />

      <PageContainer>
        {/* Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <Link href="/jobs" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'rgba(212,175,55,0.45)', fontSize: '0.83rem', textDecoration: 'none' }}>
            <ArrowLeft size={14} /> Jobs
          </Link>
          <span style={{ color: 'rgba(212,175,55,0.2)' }}>›</span>
          <span style={{ fontSize: '0.83rem', color: 'rgba(255,215,0,0.7)' }}>{extractRepoName(job.repo_name)}</span>
        </div>

        {/* Job info card */}
        <div style={{ background: 'linear-gradient(135deg, rgba(22,22,22,0.97) 0%, rgba(12,12,12,0.99) 100%)', border: '1px solid rgba(212,175,55,0.18)', borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                <h1 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffd700', fontFamily: 'JetBrains Mono, monospace' }}>
                  {job.repo_name}
                </h1>
                <JobStatusBadge status={job.status} />
              </div>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {[
                  { icon: <GitBranch size={12} />, label: job.branch },
                  { icon: <Clock size={12} />, label: formatDate(job.created_at) },
                  job.duration_seconds ? { icon: <Clock size={12} />, label: formatDuration(job.duration_seconds) } : null,
                  { label: `Attempt ${job.current_attempt ?? 0} / ${job.max_attempts}` },
                ].filter(Boolean).map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', color: 'rgba(212,175,55,0.45)' }}>
                    {item!.icon}
                    <span>{item!.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {job.total_findings > 0 && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.78rem', color: 'rgba(212,175,55,0.5)' }}>
                  {job.patched_findings} of {job.total_findings} vulnerabilities patched
                </span>
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#ffd700' }}>{patchRate}%</span>
              </div>
              <Progress value={patchRate} height={8} />
            </div>
          )}
        </div>

        <FinalDecision
          finalDecision={job.final_decision}
          reason={job.final_reason}
          repositoryChanged={job.repository_changed}
          attemptsUsed={job.current_attempt ?? 0}
          maxAttempts={job.max_attempts}
        />

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '16px' }}>
          <button style={tabStyle('stream')} onClick={() => setActiveTab('stream')}>
            <Wifi size={13} /> {job.mode === 'replay' ? 'Recorded Stream' : 'Live Stream'}
            {streamEvents.length > 0 && (
              <span style={{ background: '#d4af37', color: '#000', borderRadius: '10px', padding: '0 6px', fontSize: '0.68rem', fontWeight: 700 }}>
                {streamEvents.length}
              </span>
            )}
          </button>
          <button style={tabStyle('events')} onClick={() => setActiveTab('events')}>
            <List size={13} /> Event Log
          </button>
          <button style={tabStyle('attempts')} onClick={() => setActiveTab('attempts')}>
            <Layers size={13} /> Attempts
          </button>
          {job.status === 'completed' && (
            <Link
              href={`/audit/${job.id}`}
              style={{ ...tabStyle('events'), textDecoration: 'none', color: '#a8e063', borderColor: 'rgba(168,224,99,0.2)' }}
            >
              <FileText size={13} /> Audit Dossier
            </Link>
          )}
        </div>

        {activeTab === 'stream' && (
          <JobEvents events={streamEvents} loading={streamStatus === 'connecting'} autoScroll />
        )}
        {activeTab === 'events' && (
          <JobEvents events={logEvents} loading={eventsLoading} autoScroll={false} />
        )}
        {activeTab === 'attempts' && (
          <AttemptCard
            attempt={{
              id: job.id,
              job_id: job.id,
              attempt_number: job.current_attempt ?? 1,
              status: job.status === 'running' ? 'running' : job.status === 'completed' ? 'success' : 'failed',
              started_at: job.started_at ?? job.created_at,
              completed_at: job.completed_at,
              findings_processed: job.total_findings,
              findings_patched: job.patched_findings,
              findings_failed: job.failed_findings,
              error_message: job.error_message,
              steps: [],
            }}
            isActive={isActive}
          />
        )}
      </PageContainer>
    </>
  );
}
