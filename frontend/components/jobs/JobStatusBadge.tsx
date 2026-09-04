'use client';

import React from 'react';
import type { JobStatus } from '@/types/api';

interface JobStatusBadgeProps {
  status: JobStatus;
  size?: 'sm' | 'md';
}

const statusConfig: Record<JobStatus, { label: string; color: string; bg: string; border: string; dot: string }> = {
  pending: {
    label: 'Pending',
    color: 'rgba(203,213,225,0.7)',
    bg: 'rgba(148,163,184,0.08)',
    border: 'rgba(148,163,184,0.15)',
    dot: 'rgba(148,163,184,0.5)',
  },
  running: {
    label: 'Running',
    color: '#FDE68A',
    bg: 'rgba(251,191,36,0.1)',
    border: 'rgba(251,191,36,0.25)',
    dot: '#FBBF24',
  },
  completed: {
    label: 'Completed',
    color: '#6EE7B7',
    bg: 'rgba(52,211,153,0.1)',
    border: 'rgba(52,211,153,0.22)',
    dot: '#34D399',
  },
  failed: {
    label: 'Failed',
    color: '#FCA5A5',
    bg: 'rgba(248,113,113,0.1)',
    border: 'rgba(248,113,113,0.22)',
    dot: '#F87171',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'rgba(253,230,138,0.6)',
    bg: 'rgba(245,158,11,0.06)',
    border: 'rgba(245,158,11,0.12)',
    dot: 'rgba(245,158,11,0.4)',
  },
};

export const JobStatusBadge: React.FC<JobStatusBadgeProps> = ({ status, size = 'sm' }) => {
  const cfg = statusConfig[status] ?? statusConfig.pending;
  const isRunning = status === 'running';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: size === 'sm' ? '3px 10px' : '5px 14px',
        borderRadius: '12px',
        fontSize: size === 'sm' ? '0.72rem' : '0.82rem',
        fontWeight: 600,
        color: cfg.color,
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        letterSpacing: '0.02em',
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: cfg.dot,
          boxShadow: isRunning ? `0 0 8px ${cfg.dot}` : 'none',
          animation: isRunning ? 'pulse-glow 2s ease-in-out infinite' : 'none',
          flexShrink: 0,
        }}
      />
      {cfg.label}
    </span>
  );
};

export default JobStatusBadge;
