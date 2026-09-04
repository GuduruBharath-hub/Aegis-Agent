'use client';

import React from 'react';
import { TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { formatDate, percentage } from '@/lib/utils';
import type { PostScanResult } from '@/types/audit';

interface PostScanResultsProps {
  result: PostScanResult;
}

export const PostScanResults: React.FC<PostScanResultsProps> = ({ result }) => {
  const isClean = result.scan_passed;
  const severities = [
    { key: 'critical', color: '#ff1744' },
    { key: 'high', color: '#ff6d00' },
    { key: 'medium', color: '#ffd600' },
    { key: 'low', color: '#00e676' },
    { key: 'info', color: '#00b0ff' },
  ];

  return (
    <div style={{ background: 'rgba(13,31,56,0.8)', border: '1px solid rgba(0,212,255,0.12)', borderRadius: '10px', overflow: 'hidden' }}>
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
        <div>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e8f0fe' }}>Post-Scan Results</h4>
          <p style={{ fontSize: '0.73rem', color: 'rgba(200,220,255,0.4)', marginTop: '2px' }}>
            {result.scanner} · {formatDate(result.scanned_at)}
          </p>
        </div>
        <div
          style={{
            padding: '4px 12px',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: 700,
            color: isClean ? '#00e676' : '#ff4d6d',
            background: isClean ? 'rgba(0,230,118,0.1)' : 'rgba(255,61,113,0.1)',
            border: `1px solid ${isClean ? 'rgba(0,230,118,0.25)' : 'rgba(255,61,113,0.25)'}`,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          {isClean ? 'CLEAN' : 'ISSUES FOUND'}
        </div>
      </div>

      <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Delta stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          {[
            { label: 'Total', value: result.total_findings, color: '#e8f0fe' },
            { label: 'Resolved', value: result.resolved_findings, color: '#00e676', icon: <TrendingDown size={13} /> },
            { label: 'New', value: result.new_findings, color: result.new_findings > 0 ? '#ff4d6d' : '#00e676', icon: result.new_findings > 0 ? <TrendingUp size={13} /> : <Minus size={13} /> },
          ].map(({ label, value, color, icon }) => (
            <div key={label} style={{ textAlign: 'center', padding: '10px', background: 'rgba(7,20,40,0.4)', borderRadius: '8px', border: '1px solid rgba(0,212,255,0.08)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', color, marginBottom: '4px' }}>
                {icon}
                <span style={{ fontSize: '1.4rem', fontWeight: 700 }}>{value}</span>
              </div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(200,220,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {label}
              </div>
            </div>
          ))}
        </div>

        {/* Severity breakdown */}
        <div>
          <div style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: '10px' }}>
            By Severity
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {severities.map(({ key, color }) => {
              const count = result.findings_by_severity?.[key] ?? 0;
              const pct = percentage(count, result.total_findings);
              return (
                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '2px', background: color, flexShrink: 0 }} />
                  <span style={{ fontSize: '0.78rem', color: 'rgba(200,220,255,0.55)', width: '60px', textTransform: 'capitalize' }}>{key}</span>
                  <div style={{ flex: 1, height: '4px', background: 'rgba(0,212,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: color, opacity: count > 0 ? 0.8 : 0.15, borderRadius: '2px', transition: 'width 0.6s ease' }} />
                  </div>
                  <span style={{ fontSize: '0.78rem', color: count > 0 ? color : 'rgba(200,220,255,0.2)', fontWeight: count > 0 ? 600 : 400, width: '20px', textAlign: 'right' }}>
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PostScanResults;
