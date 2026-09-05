'use client';

import React from 'react';
import { formatDate } from '@/lib/utils';
import { RemediationSummary } from '@/components/remediation/RemediationSummary';
import type { AuditDossier } from '@/types/audit';

interface EvidenceDossierProps {
  dossier: AuditDossier;
}

export const EvidenceDossier: React.FC<EvidenceDossierProps> = ({ dossier }) => {
  const scoreColor = dossier.overall_score >= 80 ? '#00e676' : dossier.overall_score >= 60 ? '#00d4ff' : dossier.overall_score >= 40 ? '#ffab00' : '#ff4d6d';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header card */}
      <div
        style={{
          background: 'rgba(13,31,56,0.8)',
          border: '1px solid rgba(0,212,255,0.2)',
          borderRadius: '12px',
          padding: '24px',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div style={{ position: 'absolute', top: '-40px', right: '-40px', width: '160px', height: '160px', borderRadius: '50%', background: `radial-gradient(circle, ${scoreColor}12 0%, transparent 70%)`, pointerEvents: 'none' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {/* Score circle */}
          <div
            style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              border: `3px solid ${scoreColor}`,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 20px ${scoreColor}30`,
              flexShrink: 0,
            }}
          >
            <span style={{ fontSize: '1.5rem', fontWeight: 800, color: scoreColor }}>
              {Math.round(dossier.overall_score)}
            </span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(200,220,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Score
            </span>
          </div>

          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#e8f0fe', marginBottom: '4px' }}>
              Evidence Dossier
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'rgba(200,220,255,0.4)' }}>
              Job ID: <span style={{ color: '#00d4ff', fontFamily: 'JetBrains Mono, monospace' }}>{dossier.job_id}</span>
            </p>
            <p style={{ fontSize: '0.78rem', color: 'rgba(200,220,255,0.35)', marginTop: '2px' }}>
              Generated {formatDate(dossier.generated_at)}
            </p>
          </div>
        </div>
      </div>

      {/* Summary */}
      <RemediationSummary summary={dossier.summary} />
    </div>
  );
};

export default EvidenceDossier;
