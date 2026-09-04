'use client';

import React from 'react';
import { Shield, Clock, Target } from 'lucide-react';
import { Progress } from '@/components/ui/Progress';
import { formatDuration, percentage } from '@/lib/utils';
import type { AuditSummary } from '@/types/audit';

interface RemediationSummaryProps {
  summary: AuditSummary;
}

export const RemediationSummary: React.FC<RemediationSummaryProps> = ({ summary }) => {
  const patchRate = percentage(summary.vulnerabilities_patched, summary.total_vulnerabilities_found);
  const testRate = percentage(summary.regression_tests_passed, summary.regression_tests_run);
  const gateRate = percentage(summary.security_gates_passed, summary.security_gates_total);

  const stats = [
    {
      icon: <Target size={16} color="#00d4ff" />,
      label: 'Vulnerabilities',
      value: `${summary.vulnerabilities_patched} / ${summary.total_vulnerabilities_found}`,
      sub: 'patched',
      progress: patchRate,
      color: '#00d4ff',
    },
    {
      icon: <Shield size={16} color="#00e676" />,
      label: 'Regression Tests',
      value: `${summary.regression_tests_passed} / ${summary.regression_tests_run}`,
      sub: 'passed',
      progress: testRate,
      color: '#00e676',
    },
    {
      icon: <Shield size={16} color="#ffab00" />,
      label: 'Security Gates',
      value: `${summary.security_gates_passed} / ${summary.security_gates_total}`,
      sub: 'passed',
      progress: gateRate,
      color: '#ffab00',
    },
  ];

  return (
    <div
      style={{
        background: 'rgba(13,31,56,0.8)',
        border: '1px solid rgba(0,212,255,0.12)',
        borderRadius: '10px',
        padding: '18px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e8f0fe' }}>Remediation Summary</h4>
        {summary.time_to_remediate_seconds > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'rgba(200,220,255,0.45)' }}>
            <Clock size={13} />
            <span>{formatDuration(summary.time_to_remediate_seconds)}</span>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {stats.map((stat) => (
          <div key={stat.label}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {stat.icon}
                <span style={{ fontSize: '0.82rem', color: 'rgba(200,220,255,0.6)' }}>{stat.label}</span>
              </div>
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: stat.color }}>
                {stat.value} <span style={{ fontWeight: 400, color: 'rgba(200,220,255,0.35)' }}>{stat.sub}</span>
              </span>
            </div>
            <Progress value={stat.progress} color={stat.color} height={5} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default RemediationSummary;
