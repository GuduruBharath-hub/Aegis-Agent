'use client';

import React from 'react';
import { CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { formatDate, formatDuration, percentage } from '@/lib/utils';
import { Progress } from '@/components/ui/Progress';
import type { JobAttempt } from '@/types/job';

interface AttemptCardProps {
  attempt: JobAttempt;
  isActive?: boolean;
}

export const AttemptCard: React.FC<AttemptCardProps> = ({ attempt, isActive = false }) => {
  const statusIcon = {
    running: <Loader2 size={16} color="#00d4ff" style={{ animation: 'spin 0.8s linear infinite' }} />,
    success: <CheckCircle2 size={16} color="#00e676" />,
    failed: <XCircle size={16} color="#ff4d6d" />,
    timeout: <Clock size={16} color="#ffab00" />,
  }[attempt.status] ?? <Clock size={16} color="rgba(200,220,255,0.4)" />;

  const patchRate = percentage(attempt.findings_patched, attempt.findings_processed);

  return (
    <div
      style={{
        background: isActive ? 'rgba(0,212,255,0.04)' : 'rgba(7,20,40,0.5)',
        border: `1px solid ${isActive ? 'rgba(0,212,255,0.25)' : 'rgba(0,212,255,0.1)'}`,
        borderRadius: '10px',
        padding: '16px',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {statusIcon}
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: isActive ? '#00d4ff' : '#e8f0fe' }}>
            Attempt #{attempt.attempt_number}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '12px', fontSize: '0.78rem', color: 'rgba(200,220,255,0.4)' }}>
          {attempt.started_at && <span>{formatDate(attempt.started_at)}</span>}
          {attempt.duration_seconds && <span>{formatDuration(attempt.duration_seconds)}</span>}
        </div>
      </div>

      {/* Patch Progress */}
      {attempt.findings_processed > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <Progress
            value={patchRate}
            label="Patch rate"
            showLabel
            color={patchRate >= 80 ? '#00e676' : patchRate >= 50 ? '#00d4ff' : '#ffab00'}
          />
        </div>
      )}

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {[
          { label: 'Processed', value: attempt.findings_processed, color: '#e8f0fe' },
          { label: 'Patched', value: attempt.findings_patched, color: '#00e676' },
          { label: 'Failed', value: attempt.findings_failed, color: attempt.findings_failed > 0 ? '#ff4d6d' : 'rgba(200,220,255,0.3)' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {label}
            </div>
          </div>
        ))}
      </div>

      {attempt.error_message && (
        <div
          style={{
            marginTop: '12px',
            padding: '10px 12px',
            background: 'rgba(255,61,113,0.08)',
            border: '1px solid rgba(255,61,113,0.2)',
            borderRadius: '6px',
            fontSize: '0.8rem',
            color: '#ff8080',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          {attempt.error_message}
        </div>
      )}
    </div>
  );
};

export default AttemptCard;
