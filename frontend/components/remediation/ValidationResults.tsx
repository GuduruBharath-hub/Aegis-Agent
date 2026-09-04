'use client';

import React from 'react';
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { Progress } from '@/components/ui/Progress';
import { percentage } from '@/lib/utils';

interface ValidationResult {
  test_name: string;
  status: 'passed' | 'failed' | 'skipped';
  duration_ms?: number;
  message?: string;
}

interface ValidationResultsProps {
  results: ValidationResult[];
  title?: string;
}

export const ValidationResults: React.FC<ValidationResultsProps> = ({
  results,
  title = 'Validation Results',
}) => {
  const passed = results.filter((r) => r.status === 'passed').length;
  const failed = results.filter((r) => r.status === 'failed').length;
  const passRate = percentage(passed, results.length);

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
      <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(0,212,255,0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e8f0fe' }}>{title}</h4>
          <div style={{ display: 'flex', gap: '14px', fontSize: '0.8rem' }}>
            <span style={{ color: '#00e676', fontWeight: 600 }}>{passed} passed</span>
            {failed > 0 && <span style={{ color: '#ff4d6d', fontWeight: 600 }}>{failed} failed</span>}
          </div>
        </div>
        <Progress value={passRate} showLabel label="Pass rate" />
      </div>

      {/* Results list */}
      <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
        {results.map((result, i) => {
          const icon = {
            passed: <CheckCircle2 size={14} color="#00e676" />,
            failed: <XCircle size={14} color="#ff4d6d" />,
            skipped: <AlertCircle size={14} color="rgba(200,220,255,0.3)" />,
          }[result.status];

          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 18px',
                borderBottom: i < results.length - 1 ? '1px solid rgba(0,212,255,0.04)' : 'none',
                background: result.status === 'failed' ? 'rgba(255,61,113,0.04)' : 'transparent',
              }}
            >
              {icon}
              <span style={{ flex: 1, color: result.status === 'skipped' ? 'rgba(200,220,255,0.35)' : '#e8f0fe', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>
                {result.test_name}
              </span>
              {result.duration_ms && (
                <span style={{ fontSize: '0.7rem', color: 'rgba(200,220,255,0.3)' }}>
                  {result.duration_ms}ms
                </span>
              )}
              {result.message && (
                <span style={{ fontSize: '0.72rem', color: result.status === 'failed' ? '#ff8080' : 'rgba(200,220,255,0.4)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {result.message}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ValidationResults;
