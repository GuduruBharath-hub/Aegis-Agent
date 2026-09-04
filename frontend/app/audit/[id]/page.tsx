'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { EvidenceDossier } from '@/components/audit/EvidenceDossier';
import { SecurityOracle } from '@/components/audit/SecurityOracle';
import { RegressionResults } from '@/components/audit/RegressionResults';
import { PostScanResults } from '@/components/audit/PostScanResults';
import { IntegrityResults } from '@/components/audit/IntegrityResults';
import { SecurityGates } from '@/components/remediation/SecurityGates';
import { EmptyState } from '@/components/ui/EmptyState';
import api from '@/lib/api';
import type { AuditDossier } from '@/types/audit';
import { ArrowLeft, Download, FileText } from 'lucide-react';

export default function AuditPage() {
  const params = useParams();
  const jobId = params.id as string;
  const [dossier, setDossier] = useState<AuditDossier | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get(`/api/jobs/${jobId}/audit/dossier`)
      .then((res) => setDossier(res.data))
      .catch((err) => setError(err?.response?.data?.detail ?? 'Failed to load audit dossier'))
      .finally(() => setLoading(false));
  }, [jobId]);

  const handleExport = () => {
    if (!dossier) return;
    const blob = new Blob([JSON.stringify(dossier, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-dossier-${jobId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Header
        title="Evidence Dossier"
        subtitle={`Audit report for job ${jobId.slice(0, 8)}...`}
        actions={
          dossier && (
            <button
              onClick={handleExport}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '7px',
                padding: '8px 16px',
                background: 'rgba(0,255,135,0.08)',
                border: '1px solid rgba(0,255,135,0.2)',
                borderRadius: '8px',
                color: '#00ff87',
                cursor: 'pointer',
                fontSize: '0.83rem',
                fontWeight: 600,
              }}
            >
              <Download size={14} />
              Export JSON
            </button>
          )
        }
      />

      <PageContainer>
        {/* Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <Link href={`/jobs/${jobId}`} style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'rgba(200,220,255,0.45)', fontSize: '0.83rem', textDecoration: 'none' }}>
            <ArrowLeft size={14} /> Job Details
          </Link>
          <span style={{ color: 'rgba(0,212,255,0.3)' }}>›</span>
          <span style={{ fontSize: '0.83rem', color: 'rgba(200,220,255,0.65)', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <FileText size={13} /> Audit Dossier
          </span>
        </div>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{ height: '120px', background: 'rgba(0,212,255,0.04)', borderRadius: '12px', animation: 'pulse-glow 1.5s ease-in-out infinite' }} />
            ))}
          </div>
        ) : error || !dossier ? (
          <EmptyState
            variant="error"
            title="Audit dossier unavailable"
            description={error ?? 'The audit dossier for this job has not been generated yet.'}
          />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px', alignItems: 'start' }}>
            {/* Left column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <EvidenceDossier dossier={dossier} />
              <SecurityOracle oracle={dossier.security_oracle} />
              {dossier.regression_results.length > 0 && (
                <RegressionResults results={dossier.regression_results} />
              )}
            </div>

            {/* Right column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <PostScanResults result={dossier.post_scan_results} />
              <IntegrityResults result={dossier.integrity_results} />
              {dossier.security_gates.length > 0 && (
                <SecurityGates gates={dossier.security_gates} />
              )}
            </div>
          </div>
        )}
      </PageContainer>
    </>
  );
}
