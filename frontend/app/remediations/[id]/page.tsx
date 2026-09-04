'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { FindingCard } from '@/components/remediation/FindingCard';
import { PatchViewer } from '@/components/remediation/PatchViewer';
import { ValidationResults } from '@/components/remediation/ValidationResults';
import { SecurityGates } from '@/components/remediation/SecurityGates';
import { RemediationSummary } from '@/components/remediation/RemediationSummary';
import { EmptyState } from '@/components/ui/EmptyState';
import { useJob } from '@/hooks/useJob';
import { extractRepoName } from '@/lib/utils';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import type { Finding } from '@/types/finding';

export default function RemediationDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  const { job, loading, error } = useJob(jobId);

  // Mock findings for display (real data comes from backend /jobs/{id}/findings)
  const mockFindings: Finding[] = [];

  // Mock security gates
  const mockGates = [
    { id: '1', name: 'No New Critical Findings', description: 'Post-scan shows no new critical vulnerabilities', status: 'passed' as const, required: true, blocking: true },
    { id: '2', name: 'Regression Tests Pass', description: 'All regression tests must pass', status: 'passed' as const, required: true, blocking: true },
    { id: '3', name: 'Patch Coverage ≥ 80%', description: 'At least 80% of findings must be patched', status: 'pending' as const, required: false, blocking: false },
  ];

  if (loading) {
    return (
      <>
        <Header title="Remediation Details" />
        <PageContainer>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} style={{ height: '100px', background: 'rgba(0,212,255,0.04)', borderRadius: '10px', animation: 'pulse-glow 1.5s ease-in-out infinite' }} />
            ))}
          </div>
        </PageContainer>
      </>
    );
  }

  if (error || !job) {
    return (
      <>
        <Header title="Remediation Not Found" />
        <PageContainer>
          <EmptyState variant="error" title="Remediation not found" description={error ?? 'This remediation does not exist.'} />
        </PageContainer>
      </>
    );
  }

  return (
    <>
      <Header
        title={`Remediation – ${extractRepoName(job.repo_name)}`}
        subtitle={`Job ${job.id.slice(0, 8)}...`}
      />
      <PageContainer>
        {/* Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <Link href="/remediations" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'rgba(200,220,255,0.45)', fontSize: '0.83rem', textDecoration: 'none' }}>
            <ArrowLeft size={14} /> Remediations
          </Link>
          <span style={{ color: 'rgba(0,212,255,0.3)' }}>›</span>
          <span style={{ fontSize: '0.83rem', color: 'rgba(200,220,255,0.65)' }}>{extractRepoName(job.repo_name)}</span>
        </div>

        {/* Two-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px', alignItems: 'start' }}>
          {/* Left – Findings list */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#e8f0fe', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={16} color="#00d4ff" />
                Findings
                <span style={{ fontSize: '0.78rem', color: 'rgba(200,220,255,0.4)', fontWeight: 400 }}>
                  ({job.total_findings} total)
                </span>
              </h2>
            </div>

            {mockFindings.length === 0 ? (
              <EmptyState
                title="No findings loaded"
                description="Connect your backend to load real findings for this job."
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {mockFindings.map((finding) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    selected={selectedFinding?.id === finding.id}
                    onClick={() => setSelectedFinding(selectedFinding?.id === finding.id ? null : finding)}
                  />
                ))}
              </div>
            )}

            {/* Patch viewer for selected finding */}
            {selectedFinding?.patch && (
              <div style={{ marginTop: '16px' }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e8f0fe', marginBottom: '10px' }}>Patch Preview</h3>
                <PatchViewer patch={selectedFinding.patch} />
              </div>
            )}
          </div>

          {/* Right – Summary panel */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <RemediationSummary
              summary={{
                total_vulnerabilities_found: job.total_findings,
                vulnerabilities_patched: job.patched_findings,
                vulnerabilities_failed: job.failed_findings,
                patch_success_rate: job.total_findings > 0 ? (job.patched_findings / job.total_findings) * 100 : 0,
                regression_tests_run: 0,
                regression_tests_passed: 0,
                security_gates_passed: mockGates.filter((g) => g.status === 'passed').length,
                security_gates_total: mockGates.length,
                time_to_remediate_seconds: job.duration_seconds ?? 0,
              }}
            />

            <SecurityGates gates={mockGates} />

            {job.status === 'completed' && (
              <Link
                href={`/audit/${job.id}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '12px',
                  background: 'linear-gradient(135deg, rgba(0,255,135,0.12), rgba(0,255,135,0.06))',
                  border: '1px solid rgba(0,255,135,0.25)',
                  borderRadius: '10px',
                  color: '#00ff87',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}
              >
                <ShieldCheck size={15} />
                View Evidence Dossier →
              </Link>
            )}
          </div>
        </div>
      </PageContainer>
    </>
  );
}
