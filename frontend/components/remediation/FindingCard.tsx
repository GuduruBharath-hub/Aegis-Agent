'use client';

import React from 'react';
import { FileCode, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { capitalize, formatRelativeTime } from '@/lib/utils';
import type { Finding } from '@/types/finding';
import type { Severity, FindingStatus } from '@/types/api';

interface FindingCardProps {
  finding: Finding;
  onClick?: () => void;
  selected?: boolean;
}

const severityVariant: Record<Severity, 'critical' | 'high' | 'medium' | 'low' | 'info'> = {
  critical: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
  info: 'info',
};

const statusVariant: Record<FindingStatus, 'running' | 'completed' | 'warning' | 'pending' | 'default'> = {
  open: 'running',
  in_remediation: 'running',
  patched: 'completed',
  verified: 'completed',
  wont_fix: 'default',
};

export const FindingCard: React.FC<FindingCardProps> = ({ finding, onClick, selected = false }) => {
  return (
    <div
      onClick={onClick}
      style={{
        background: selected ? 'rgba(0,212,255,0.06)' : 'rgba(7,20,40,0.5)',
        border: `1px solid ${selected ? 'rgba(0,212,255,0.3)' : 'rgba(0,212,255,0.1)'}`,
        borderRadius: '10px',
        padding: '14px 16px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
      }}
    >
      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginBottom: '8px' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
            <Badge variant={severityVariant[finding.severity]} />
            <Badge variant={statusVariant[finding.status] ?? 'default'}>
              {capitalize(finding.status)}
            </Badge>
            {finding.cwe_id && (
              <span style={{ fontSize: '0.7rem', color: 'rgba(200,220,255,0.4)', fontFamily: 'JetBrains Mono, monospace' }}>
                {finding.cwe_id}
              </span>
            )}
          </div>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e8f0fe', lineHeight: 1.3 }}>
            {finding.title}
          </h4>
        </div>
      </div>

      {/* File path */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
        <FileCode size={13} color="rgba(200,220,255,0.35)" />
        <span
          style={{
            fontSize: '0.78rem',
            color: 'rgba(0,212,255,0.6)',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          {finding.file_path}:{finding.line_start}
          {finding.line_end !== finding.line_start && `-${finding.line_end}`}
        </span>
      </div>

      {/* Description excerpt */}
      <p
        style={{
          fontSize: '0.8rem',
          color: 'rgba(200,220,255,0.5)',
          lineHeight: 1.5,
          marginBottom: '10px',
          overflow: 'hidden',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}
      >
        {finding.description}
      </p>

      {/* Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: '8px', fontSize: '0.72rem', color: 'rgba(200,220,255,0.35)' }}>
          <span>{finding.scanner}</span>
          <span>·</span>
          <span>{finding.rule_id}</span>
        </div>
        <span style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.3)' }}>
          {formatRelativeTime(finding.updated_at)}
        </span>
      </div>
    </div>
  );
};

export default FindingCard;
