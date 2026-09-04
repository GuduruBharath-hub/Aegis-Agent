'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { StatCard } from '@/components/dashboard/StatCard';
import { JobTable } from '@/components/dashboard/JobTable';
import { SecurityOverview } from '@/components/dashboard/SecurityOverview';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { Modal } from '@/components/ui/Modal';
import { StartJobForm } from '@/components/jobs/StartJobForm';
import { getJobs } from '@/lib/jobs';
import { startDemo } from '@/lib/jobs';
import type { JobSummary, Job } from '@/types/job';
import {
  ShieldCheck,
  Briefcase,
  Activity,
  Target,
  Plus,
} from 'lucide-react';
import { useRouter } from 'next/navigation';

const SEVERITY_DATA = [
  { name: 'Critical', value: 3, color: '#EF4444' },
  { name: 'High', value: 12, color: '#F97316' },
  { name: 'Medium', value: 27, color: '#FBBF24' },
  { name: 'Low', value: 45, color: '#34D399' },
  { name: 'Info', value: 8, color: '#60A5FA' },
];

export default function DashboardPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [showStartJob, setShowStartJob] = useState(false);
  const [runningDemo, setRunningDemo] = useState<string | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  useEffect(() => {
    getJobs({ page: 1, page_size: 10 })
      .then((res) => setJobs(res.items))
      .catch(() => setJobs([]))
      .finally(() => setLoadingJobs(false));
  }, []);

  const handleJobStarted = (job: Job) => {
    setShowStartJob(false);
    router.push(`/jobs/${job.id}`);
  };

  const launchDemo = async (scenario: string) => {
    setRunningDemo(scenario);
    setDemoError(null);
    try {
      const job = await startDemo(scenario);
      router.push(`/jobs/${job.id}`);
    } catch (error: unknown) {
      setDemoError(error instanceof Error ? error.message : 'Could not start demo');
      setRunningDemo(null);
    }
  };

  const runningJobs = jobs.filter((j) => j.status === 'running').length;
  const completedJobs = jobs.filter((j) => j.status === 'completed').length;
  const totalPatched = jobs.reduce((acc, j) => acc + j.patched_findings, 0);

  return (
    <>
      <Header
        title="Dashboard"
        subtitle="Security remediation overview"
        actions={
          <button
            onClick={() => setShowStartJob(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 20px',
              /* Gradient button with radial glow */
              background: 'linear-gradient(135deg, rgba(251,191,36,0.18) 0%, rgba(180,83,9,0.1) 100%)',
              border: '1px solid rgba(251,191,36,0.4)',
              borderRadius: '10px',
              color: '#FDE68A',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
              letterSpacing: '0.02em',
              boxShadow: '0 0 20px rgba(251,191,36,0.12), 0 0 40px rgba(251,191,36,0.04)',
              transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <Plus size={15} />
            New Job
          </button>
        }
      />

      <PageContainer>
        <section style={{ marginBottom: '24px', padding: '20px', border: '1px solid rgba(251,191,36,0.18)', borderRadius: '14px', background: 'linear-gradient(135deg, rgba(251,191,36,0.08), rgba(2,6,23,0.8))' }}>
          <div style={{ marginBottom: '14px' }}>
            <h2 style={{ color: '#FDE68A', fontSize: '1rem', margin: 0 }}>Launch the evidence loop</h2>
            <p style={{ color: 'rgba(203,213,225,0.58)', fontSize: '0.82rem', margin: '5px 0 0' }}>
              Three live paths: verified repair, bounded escalation, and policy refusal.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '10px' }}>
            {[
              ['sql_retry', 'Demo A · Self-correct', 'Reject a regression, retry, then verify'],
              ['unsolvable', 'Demo B · Escalate', 'Stop after evidence cannot satisfy both requirements'],
              ['policy_hidden_test', 'Demo C · Policy block', 'Deny an attempt to cross the hidden-test boundary'],
            ].map(([scenario, title, description]) => (
              <button key={scenario} onClick={() => launchDemo(scenario)} disabled={runningDemo !== null} style={{ padding: '14px', textAlign: 'left', borderRadius: '10px', border: '1px solid rgba(251,191,36,0.18)', background: 'rgba(15,23,42,0.75)', color: '#F8FAFC', cursor: runningDemo ? 'wait' : 'pointer', opacity: runningDemo && runningDemo !== scenario ? 0.5 : 1 }}>
                <span style={{ display: 'block', color: '#FBBF24', fontWeight: 700, fontSize: '0.82rem' }}>{runningDemo === scenario ? 'Starting…' : title}</span>
                <span style={{ display: 'block', marginTop: '5px', color: 'rgba(203,213,225,0.55)', fontSize: '0.74rem', lineHeight: 1.45 }}>{description}</span>
              </button>
            ))}
          </div>
          {demoError && <div style={{ marginTop: '10px', color: '#FCA5A5', fontSize: '0.78rem' }}>{demoError}</div>}
        </section>

        {/* Stat Cards */}
        <div className="grid-4" style={{ marginBottom: '24px' }}>
          <StatCard
            title="Active Jobs"
            value={loadingJobs ? '—' : runningJobs}
            subtitle="currently running"
            icon={<Briefcase size={16} />}
            accentColor="#FBBF24"
            trend={12}
            trendLabel="vs last week"
            loading={loadingJobs}
          />
          <StatCard
            title="Completed Today"
            value={loadingJobs ? '—' : completedJobs}
            subtitle="jobs finished"
            icon={<ShieldCheck size={16} />}
            accentColor="#34D399"
            trend={8}
            loading={loadingJobs}
          />
          <StatCard
            title="Vulnerabilities Patched"
            value={loadingJobs ? '—' : totalPatched}
            subtitle="total fixed"
            icon={<Target size={16} />}
            accentColor="#60A5FA"
            trend={-3}
            trendLabel="new this week"
            loading={loadingJobs}
          />
          <StatCard
            title="Success Rate"
            value={loadingJobs ? '—' : '94%'}
            subtitle="patch success"
            icon={<Activity size={16} />}
            accentColor="#F59E0B"
            trend={2}
            loading={loadingJobs}
          />
        </div>

        {/* Main content row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px', marginBottom: '20px' }}>
          <JobTable jobs={jobs} loading={loadingJobs} />
          <SecurityOverview data={SEVERITY_DATA} />
        </div>

        {/* Activity */}
        <RecentActivity />
      </PageContainer>

      {/* Start Job Modal */}
      <Modal
        open={showStartJob}
        onClose={() => setShowStartJob(false)}
        title="Start New Remediation Job"
      >
        <StartJobForm
          onJobStarted={handleJobStarted}
          onCancel={() => setShowStartJob(false)}
        />
      </Modal>
    </>
  );
}
