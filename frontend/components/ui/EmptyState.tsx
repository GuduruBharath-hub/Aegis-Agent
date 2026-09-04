'use client';

import React from 'react';
import { InboxIcon, SearchX, AlertTriangle, FileQuestion } from 'lucide-react';

type EmptyVariant = 'empty' | 'search' | 'error' | 'not-found';

interface EmptyStateProps {
  variant?: EmptyVariant;
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

const variantConfig: Record<EmptyVariant, { icon: React.ReactNode; defaultTitle: string }> = {
  empty: { icon: <InboxIcon size={40} strokeWidth={1} />, defaultTitle: 'No data' },
  search: { icon: <SearchX size={40} strokeWidth={1} />, defaultTitle: 'No results' },
  error: { icon: <AlertTriangle size={40} strokeWidth={1} />, defaultTitle: 'Something went wrong' },
  'not-found': { icon: <FileQuestion size={40} strokeWidth={1} />, defaultTitle: 'Not found' },
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  variant = 'empty',
  title,
  description,
  icon,
  action,
}) => {
  const cfg = variantConfig[variant];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        color: 'rgba(148,163,184,0.4)',
      }}
    >
      <div style={{ marginBottom: '14px', opacity: 0.5 }}>{icon ?? cfg.icon}</div>
      <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'rgba(248,250,252,0.6)', marginBottom: '6px' }}>
        {title ?? cfg.defaultTitle}
      </h3>
      {description && (
        <p style={{ fontSize: '0.85rem', color: 'rgba(148,163,184,0.5)', maxWidth: '360px', lineHeight: 1.5 }}>
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: '16px' }}>{action}</div>}
    </div>
  );
};

export default EmptyState;
