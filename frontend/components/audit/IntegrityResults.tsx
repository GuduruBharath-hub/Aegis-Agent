'use client';

import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { Progress } from '@/components/ui/Progress';
import type { IntegrityResult } from '@/types/audit';

interface IntegrityResultsProps {
  result: IntegrityResult;
}

export const IntegrityResults: React.FC<IntegrityResultsProps> = ({ result }) => {
  const checks = [
    { label: 'File Hash Valid', value: result.file_hash_valid },
    { label: 'Signature Valid', value: result.signature_valid },
    { label: 'Dependency Scan Clean', value: result.dependency_scan_clean },
    { label: 'Secret Scan Clean', value: result.secret_scan_clean },
  ];

  return (
    <div style={{ background: 'rgba(13,31,56,0.8)', border: '1px solid rgba(0,212,255,0.12)', borderRadius: '10px', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(0,212,255,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e8f0fe' }}>Integrity Check</h4>
          <span style={{ fontSize: '0.875rem', fontWeight: 700, color: result.integrity_score >= 80 ? '#00e676' : '#ffab00' }}>
            {result.integrity_score.toFixed(1)}%
          </span>
        </div>
        <Progress value={result.integrity_score} color={result.integrity_score >= 80 ? '#00e676' : '#ffab00'} showLabel />
      </div>

      <div style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Check boxes */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {checks.map(({ label, value }) => (
            <div
              key={label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                background: value ? 'rgba(0,230,118,0.05)' : 'rgba(255,61,113,0.06)',
                border: `1px solid ${value ? 'rgba(0,230,118,0.15)' : 'rgba(255,61,113,0.15)'}`,
                borderRadius: '8px',
              }}
            >
              {value ? (
                <CheckCircle2 size={13} color="#00e676" />
              ) : (
                <XCircle size={13} color="#ff4d6d" />
              )}
              <span style={{ fontSize: '0.78rem', color: 'rgba(200,220,255,0.65)' }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Issues */}
        {result.issues && result.issues.length > 0 && (
          <div>
            <div style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: '8px' }}>
              Issues ({result.issues.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {result.issues.map((issue, i) => (
                <div
                  key={i}
                  style={{
                    padding: '8px 12px',
                    background: 'rgba(255,171,0,0.06)',
                    border: '1px solid rgba(255,171,0,0.15)',
                    borderRadius: '6px',
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'flex-start',
                  }}
                >
                  <AlertTriangle size={13} color="#ffab00" style={{ marginTop: '1px', flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: '0.8rem', color: '#e8f0fe', marginBottom: '2px' }}>{issue.check_name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'rgba(200,220,255,0.5)' }}>{issue.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntegrityResults;
