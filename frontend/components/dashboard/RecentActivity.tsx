'use client';

import React from 'react';
import { ShieldCheck, Bug, Wrench, CheckCircle2 } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

interface ActivityItem {
  id: string;
  type: 'scan' | 'finding' | 'patch' | 'complete';
  title: string;
  description: string;
  timestamp: string;
}

const iconConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  scan: { icon: <ShieldCheck size={14} />, color: '#FBBF24' },
  finding: { icon: <Bug size={14} />, color: '#F97316' },
  patch: { icon: <Wrench size={14} />, color: '#60A5FA' },
  complete: { icon: <CheckCircle2 size={14} />, color: '#34D399' },
};

const MOCK_ACTIVITIES: ActivityItem[] = [
  { id: '1', type: 'scan', title: 'Scan started', description: 'auth-service repository', timestamp: new Date(Date.now() - 300000).toISOString() },
  { id: '2', type: 'finding', title: 'SQL Injection found', description: 'Critical – login.py:42', timestamp: new Date(Date.now() - 600000).toISOString() },
  { id: '3', type: 'patch', title: 'Patch applied', description: 'XSS in search.tsx', timestamp: new Date(Date.now() - 900000).toISOString() },
  { id: '4', type: 'complete', title: 'Job completed', description: 'payment-api – 12 fixed', timestamp: new Date(Date.now() - 1800000).toISOString() },
  { id: '5', type: 'finding', title: 'Path Traversal', description: 'High – file_handler.py:88', timestamp: new Date(Date.now() - 3600000).toISOString() },
];

export const RecentActivity: React.FC = () => {
  return (
    <div
      style={{
        background: `
          linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%),
          linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.98) 100%)
        `,
        border: '1px solid rgba(251,191,36,0.1)',
        borderRadius: '14px',
        overflow: 'hidden',
        boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 32px rgba(0,0,0,0.5)',
      }}
    >
      <div
        style={{
          padding: '18px 22px',
          borderBottom: '1px solid rgba(251,191,36,0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <h3
          style={{
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'rgba(148,163,184,0.7)',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
          }}
        >
          Recent Activity
        </h3>
        <span style={{ fontSize: '0.72rem', color: 'rgba(148,163,184,0.4)' }}>Last 24h</span>
      </div>

      <div style={{ padding: '6px 0' }}>
        {MOCK_ACTIVITIES.map((activity, i) => {
          const cfg = iconConfig[activity.type];
          return (
            <div
              key={activity.id}
              style={{
                display: 'flex',
                gap: '14px',
                padding: '14px 22px',
                borderBottom: i < MOCK_ACTIVITIES.length - 1 ? '1px solid rgba(251,191,36,0.04)' : 'none',
                transition: 'background 0.15s ease',
              }}
            >
              <div
                style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '8px',
                  background: `linear-gradient(135deg, ${cfg.color}14 0%, ${cfg.color}06 100%)`,
                  border: `1px solid ${cfg.color}18`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: cfg.color,
                  flexShrink: 0,
                }}
              >
                {cfg.icon}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 500, color: '#F8FAFC', marginBottom: '2px' }}>
                  {activity.title}
                </div>
                <div
                  style={{
                    color: 'rgba(148,163,184,0.55)',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '0.74rem',
                  }}
                >
                  {activity.description}
                </div>
              </div>
              <div
                style={{
                  fontSize: '0.72rem',
                  color: 'rgba(148,163,184,0.4)',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                {formatRelativeTime(activity.timestamp)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RecentActivity;
