'use client';

import React from 'react';
import { ShieldCheck, ShieldX, ShieldAlert, Brain } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import type { SecurityOracle as SecurityOracleType } from '@/types/audit';

interface SecurityOracleProps {
  oracle: SecurityOracleType;
}

const verdictConfig = {
  approved: { icon: ShieldCheck, color: '#00e676', label: 'APPROVED', bg: 'rgba(0,230,118,0.08)', border: 'rgba(0,230,118,0.25)' },
  rejected: { icon: ShieldX, color: '#ff4d6d', label: 'REJECTED', bg: 'rgba(255,61,113,0.08)', border: 'rgba(255,61,113,0.25)' },
  needs_review: { icon: ShieldAlert, color: '#ffab00', label: 'NEEDS REVIEW', bg: 'rgba(255,171,0,0.08)', border: 'rgba(255,171,0,0.25)' },
};

export const SecurityOracle: React.FC<SecurityOracleProps> = ({ oracle }) => {
  const cfg = verdictConfig[oracle.verdict] ?? verdictConfig.needs_review;
  const VerdictIcon = cfg.icon;

  return (
    <div
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: '12px',
        padding: '20px',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <div
          style={{
            width: '44px',
            height: '44px',
            borderRadius: '10px',
            background: `${cfg.color}15`,
            border: `1px solid ${cfg.color}30`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 0 16px ${cfg.color}20`,
          }}
        >
          <VerdictIcon size={22} color={cfg.color} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: cfg.color }}>
              {cfg.label}
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Brain size={12} color="rgba(200,220,255,0.4)" />
              <span style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.4)' }}>
                AI Oracle · {Math.round(oracle.confidence * 100)}% confidence
              </span>
            </div>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'rgba(200,220,255,0.4)', marginTop: '2px' }}>
            Evaluated {formatDate(oracle.evaluated_at)}
          </p>
        </div>
      </div>

      {/* Reasoning */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.45)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '6px', fontWeight: 600 }}>
          Reasoning
        </div>
        <p style={{ fontSize: '0.85rem', color: 'rgba(200,220,255,0.7)', lineHeight: 1.6 }}>
          {oracle.reasoning}
        </p>
      </div>

      {/* Recommendations */}
      {oracle.recommendations.length > 0 && (
        <div>
          <div style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.45)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '8px', fontWeight: 600 }}>
            Recommendations
          </div>
          <ul style={{ display: 'flex', flexDirection: 'column', gap: '6px', listStyle: 'none' }}>
            {oracle.recommendations.map((rec, i) => (
              <li key={i} style={{ display: 'flex', gap: '8px', fontSize: '0.82rem', color: 'rgba(200,220,255,0.6)', lineHeight: 1.4 }}>
                <span style={{ color: cfg.color, flexShrink: 0 }}>→</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default SecurityOracle;
