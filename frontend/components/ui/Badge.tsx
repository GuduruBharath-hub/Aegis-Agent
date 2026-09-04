'use client';

import React from 'react';
import { capitalize } from '@/lib/utils';

export type BadgeVariant =
  | 'critical' | 'high' | 'medium' | 'low' | 'info'
  | 'running' | 'completed' | 'failed' | 'pending' | 'cancelled'
  | 'success' | 'warning' | 'default';

interface BadgeProps {
  variant?: BadgeVariant;
  children?: React.ReactNode;
  label?: string;
  dot?: boolean;
  style?: React.CSSProperties;
}

const variantStyles: Record<BadgeVariant, React.CSSProperties> = {
  critical: { background: 'rgba(255,23,68,0.15)', color: '#ff4d6d', borderColor: 'rgba(255,23,68,0.3)' },
  high: { background: 'rgba(255,109,0,0.15)', color: '#ff9030', borderColor: 'rgba(255,109,0,0.3)' },
  medium: { background: 'rgba(255,214,0,0.12)', color: '#ffd600', borderColor: 'rgba(255,214,0,0.25)' },
  low: { background: 'rgba(0,230,118,0.12)', color: '#00e676', borderColor: 'rgba(0,230,118,0.25)' },
  info: { background: 'rgba(0,176,255,0.12)', color: '#00b0ff', borderColor: 'rgba(0,176,255,0.25)' },
  running: { background: 'rgba(0,212,255,0.12)', color: '#00d4ff', borderColor: 'rgba(0,212,255,0.25)' },
  completed: { background: 'rgba(0,230,118,0.12)', color: '#00e676', borderColor: 'rgba(0,230,118,0.25)' },
  failed: { background: 'rgba(255,61,113,0.12)', color: '#ff4d6d', borderColor: 'rgba(255,61,113,0.25)' },
  pending: { background: 'rgba(150,180,220,0.1)', color: 'rgba(200,220,255,0.65)', borderColor: 'rgba(150,180,220,0.15)' },
  cancelled: { background: 'rgba(255,171,0,0.12)', color: '#ffab00', borderColor: 'rgba(255,171,0,0.25)' },
  success: { background: 'rgba(0,230,118,0.12)', color: '#00e676', borderColor: 'rgba(0,230,118,0.25)' },
  warning: { background: 'rgba(255,171,0,0.12)', color: '#ffab00', borderColor: 'rgba(255,171,0,0.25)' },
  default: { background: 'rgba(150,180,220,0.1)', color: 'rgba(200,220,255,0.65)', borderColor: 'rgba(150,180,220,0.15)' },
};

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  children,
  label,
  dot = false,
  style,
}) => {
  const vs = variantStyles[variant] ?? variantStyles.default;
  const text = children ?? label ?? capitalize(variant);

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        padding: '2px 10px',
        borderRadius: '20px',
        fontSize: '0.74rem',
        fontWeight: 600,
        letterSpacing: '0.04em',
        border: '1px solid',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        ...vs,
        ...style,
      }}
    >
      {dot && (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: 'currentColor',
            display: 'inline-block',
            animation: variant === 'running' ? 'pulse-glow 2s ease-in-out infinite' : undefined,
          }}
        />
      )}
      {text}
    </span>
  );
};

export default Badge;
