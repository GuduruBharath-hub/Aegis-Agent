'use client';

import React from 'react';
import { CheckCircle2, XCircle, Circle, Loader2 } from 'lucide-react';
import { formatDate, formatDuration } from '@/lib/utils';
import type { JobAttempt } from '@/types/job';

interface JobTimelineProps {
  attempts: JobAttempt[];
  currentAttempt?: number;
}

const stepStatusIcon = (status: string) => {
  switch (status) {
    case 'completed': return <CheckCircle2 size={14} color="#00e676" />;
    case 'running': return <Loader2 size={14} color="#00d4ff" style={{ animation: 'spin 0.8s linear infinite' }} />;
    case 'failed': return <XCircle size={14} color="#ff4d6d" />;
    case 'skipped': return <Circle size={14} color="rgba(200,220,255,0.3)" />;
    default: return <Circle size={14} color="rgba(200,220,255,0.2)" />;
  }
};

export const JobTimeline: React.FC<JobTimelineProps> = ({ attempts, currentAttempt }) => {
  if (!attempts || attempts.length === 0) {
    return (
      <div style={{ padding: '24px', color: 'rgba(200,220,255,0.4)', fontSize: '0.875rem', textAlign: 'center' }}>
        No attempts yet.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {attempts.map((attempt) => (
        <div
          key={attempt.id}
          style={{
            background: 'rgba(7,20,40,0.6)',
            border: `1px solid ${attempt.attempt_number === currentAttempt ? 'rgba(0,212,255,0.3)' : 'rgba(0,212,255,0.1)'}`,
            borderRadius: '10px',
            overflow: 'hidden',
          }}
        >
          {/* Attempt header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              borderBottom: '1px solid rgba(0,212,255,0.06)',
              background: attempt.attempt_number === currentAttempt ? 'rgba(0,212,255,0.05)' : 'transparent',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: attempt.attempt_number === currentAttempt ? '#00d4ff' : 'rgba(200,220,255,0.6)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                Attempt #{attempt.attempt_number}
              </span>
              <span
                style={{
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  background: attempt.status === 'success' ? 'rgba(0,230,118,0.12)' : attempt.status === 'failed' ? 'rgba(255,61,113,0.12)' : 'rgba(0,212,255,0.12)',
                  color: attempt.status === 'success' ? '#00e676' : attempt.status === 'failed' ? '#ff4d6d' : '#00d4ff',
                }}
              >
                {attempt.status}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.78rem', color: 'rgba(200,220,255,0.45)' }}>
              {attempt.completed_at && (
                <span>{formatDate(attempt.completed_at)}</span>
              )}
              {attempt.duration_seconds && (
                <span>{formatDuration(attempt.duration_seconds)}</span>
              )}
            </div>
          </div>

          {/* Steps */}
          {attempt.steps && attempt.steps.length > 0 && (
            <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {attempt.steps
                .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
                .map((step) => (
                  <div
                    key={step.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                    }}
                  >
                    {stepStatusIcon(step.status)}
                    <span
                      style={{
                        flex: 1,
                        fontSize: '0.82rem',
                        color: step.status === 'pending' ? 'rgba(200,220,255,0.35)' : 'rgba(200,220,255,0.75)',
                      }}
                    >
                      {step.display_name || step.name}
                    </span>
                    {step.duration_ms && (
                      <span style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.3)' }}>
                        {step.duration_ms}ms
                      </span>
                    )}
                    {step.message && (
                      <span style={{ fontSize: '0.72rem', color: step.status === 'failed' ? '#ff4d6d' : 'rgba(200,220,255,0.4)' }}>
                        {step.message}
                      </span>
                    )}
                  </div>
                ))}
            </div>
          )}

          {/* Stats */}
          <div
            style={{
              display: 'flex',
              gap: '16px',
              padding: '10px 16px',
              borderTop: '1px solid rgba(0,212,255,0.06)',
              background: 'rgba(2,11,24,0.2)',
            }}
          >
            <div style={{ display: 'flex', gap: '4px', fontSize: '0.78rem', color: 'rgba(200,220,255,0.45)' }}>
              <span>Processed:</span>
              <span style={{ color: '#e8f0fe', fontWeight: 600 }}>{attempt.findings_processed}</span>
            </div>
            <div style={{ display: 'flex', gap: '4px', fontSize: '0.78rem', color: 'rgba(200,220,255,0.45)' }}>
              <span>Patched:</span>
              <span style={{ color: '#00e676', fontWeight: 600 }}>{attempt.findings_patched}</span>
            </div>
            <div style={{ display: 'flex', gap: '4px', fontSize: '0.78rem', color: 'rgba(200,220,255,0.45)' }}>
              <span>Failed:</span>
              <span style={{ color: attempt.findings_failed > 0 ? '#ff4d6d' : 'rgba(200,220,255,0.4)', fontWeight: 600 }}>{attempt.findings_failed}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default JobTimeline;
