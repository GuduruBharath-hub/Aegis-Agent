'use client';

import React from 'react';
import { CheckCircle2, XCircle, Clock, SkipForward } from 'lucide-react';
import type { SecurityGate } from '@/types/audit';
import type { GateStatus } from '@/types/api';

interface SecurityGatesProps {
  gates: SecurityGate[];
}

const gateIcon: Record<GateStatus, React.ReactNode> = {
  passed: <CheckCircle2 size={16} color="#00e676" />,
  failed: <XCircle size={16} color="#ff4d6d" />,
  pending: <Clock size={16} color="rgba(200,220,255,0.4)" />,
  skipped: <SkipForward size={16} color="rgba(200,220,255,0.3)" />,
};

const gateBorderColor: Record<GateStatus, string> = {
  passed: 'rgba(0,230,118,0.2)',
  failed: 'rgba(255,61,113,0.2)',
  pending: 'rgba(0,212,255,0.1)',
  skipped: 'rgba(200,220,255,0.08)',
};

export const SecurityGates: React.FC<SecurityGatesProps> = ({ gates }) => {
  const allPassed = gates.every((g) => g.status === 'passed' || g.status === 'skipped');
  const anyFailed = gates.some((g) => g.status === 'failed');

  return (
    <div
      style={{
        background: 'rgba(13,31,56,0.8)',
        border: '1px solid rgba(0,212,255,0.12)',
        borderRadius: '10px',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(0,212,255,0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e8f0fe' }}>Security Gates</h4>
        <span
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: anyFailed ? '#ff4d6d' : allPassed ? '#00e676' : '#00d4ff',
            padding: '3px 10px',
            background: anyFailed ? 'rgba(255,61,113,0.1)' : allPassed ? 'rgba(0,230,118,0.1)' : 'rgba(0,212,255,0.1)',
            borderRadius: '12px',
            border: `1px solid ${anyFailed ? 'rgba(255,61,113,0.25)' : allPassed ? 'rgba(0,230,118,0.25)' : 'rgba(0,212,255,0.25)'}`,
          }}
        >
          {anyFailed ? 'BLOCKED' : allPassed ? 'ALL PASSED' : 'IN PROGRESS'}
        </span>
      </div>

      {/* Gates list */}
      <div style={{ padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {gates.map((gate) => (
          <div
            key={gate.id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '12px 14px',
              background: 'rgba(7,20,40,0.4)',
              border: `1px solid ${gateBorderColor[gate.status] ?? 'rgba(0,212,255,0.08)'}`,
              borderRadius: '8px',
            }}
          >
            <div style={{ paddingTop: '1px', flexShrink: 0 }}>
              {gateIcon[gate.status]}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#e8f0fe' }}>
                  {gate.name}
                </span>
                {gate.required && (
                  <span style={{ fontSize: '0.65rem', color: '#ffab00', border: '1px solid rgba(255,171,0,0.25)', borderRadius: '4px', padding: '1px 5px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Required
                  </span>
                )}
                {gate.blocking && (
                  <span style={{ fontSize: '0.65rem', color: '#ff4d6d', border: '1px solid rgba(255,61,113,0.25)', borderRadius: '4px', padding: '1px 5px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Blocking
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.78rem', color: 'rgba(200,220,255,0.45)', lineHeight: 1.4 }}>
                {gate.message || gate.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SecurityGates;
