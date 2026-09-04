'use client';

import React from 'react';
import { CheckCircle2, XCircle, AlertCircle, SkipForward } from 'lucide-react';
import { percentage } from '@/lib/utils';
import { Progress } from '@/components/ui/Progress';
import type { RegressionResult } from '@/types/audit';

interface RegressionResultsProps {
  results: RegressionResult[];
}

export const RegressionResults: React.FC<RegressionResultsProps> = ({ results }) => {
  const passed = results.filter((r) => r.status === 'passed').length;
  const failed = results.filter((r) => r.status === 'failed').length;
  const regressions = results.filter((r) => r.is_regression).length;
  const passRate = percentage(passed, results.length);

  const statusIcon = (status: string, isRegression: boolean) => {
    if (isRegression) return <AlertCircle size={14} color="#ffab00" />;
    switch (status) {
      case 'passed': return <CheckCircle2 size={14} color="#00e676" />;
      case 'failed': return <XCircle size={14} color="#ff4d6d" />;
      case 'skipped': return <SkipForward size={14} color="rgba(200,220,255,0.3)" />;
      default: return <AlertCircle size={14} color="#ffab00" />;
    }
  };

  return (
    <div style={{ background: 'rgba(13,31,56,0.8)', border: '1px solid rgba(0,212,255,0.12)', borderRadius: '10px', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(0,212,255,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e8f0fe' }}>Regression Tests</h4>
          <div style={{ display: 'flex', gap: '14px', fontSize: '0.78rem' }}>
            <span style={{ color: '#00e676', fontWeight: 600 }}>{passed} passed</span>
            {failed > 0 && <span style={{ color: '#ff4d6d', fontWeight: 600 }}>{failed} failed</span>}
            {regressions > 0 && <span style={{ color: '#ffab00', fontWeight: 600 }}>{regressions} regressions</span>}
          </div>
        </div>
        <Progress value={passRate} />
      </div>

      {/* Results */}
      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {results.map((result, i) => (
          <div
            key={result.id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              padding: '10px 18px',
              borderBottom: i < results.length - 1 ? '1px solid rgba(0,212,255,0.04)' : 'none',
              background: result.is_regression ? 'rgba(255,171,0,0.04)' : result.status === 'failed' ? 'rgba(255,61,113,0.04)' : 'transparent',
            }}
          >
            <div style={{ paddingTop: '1px' }}>{statusIcon(result.status, result.is_regression)}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.8rem', color: '#e8f0fe', fontFamily: 'JetBrains Mono, monospace' }}>
                {result.test_name}
              </div>
              {result.error_message && (
                <div style={{ fontSize: '0.72rem', color: '#ff8080', marginTop: '2px' }}>
                  {result.error_message}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.7rem', color: 'rgba(200,220,255,0.3)' }}>{result.duration_ms}ms</span>
              {result.is_regression && (
                <span style={{ fontSize: '0.65rem', color: '#ffab00', border: '1px solid rgba(255,171,0,0.3)', borderRadius: '4px', padding: '1px 6px' }}>
                  REGRESSION
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RegressionResults;
