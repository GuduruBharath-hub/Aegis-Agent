'use client';

import React from 'react';
import { Hand, ShieldAlert, GitPullRequest, LockKeyhole } from 'lucide-react';

interface FinalDecisionProps {
  finalDecision: string | null;
  reason: string | null;
  repositoryChanged: boolean;
  attemptsUsed: number;
  maxAttempts: number;
}

const reasonText: Record<string, string> = {
  retry_budget_exhausted: 'No candidate earned delivery within the bounded retry budget.',
  not_reproduced: 'The scanner finding could not be reproduced, so no patch was attempted.',
  no_supported_finding: 'No finding matched a supported verification adapter.',
};

export const FinalDecision: React.FC<FinalDecisionProps> = ({
  finalDecision,
  reason,
  repositoryChanged,
  attemptsUsed,
  maxAttempts,
}) => {
  if (finalDecision !== 'escalated' && finalDecision !== 'policy_rejected') return null;

  const policyBlocked = finalDecision === 'policy_rejected';
  const accent = policyBlocked ? '#fb7185' : '#fbbf24';
  const Icon = policyBlocked ? ShieldAlert : Hand;
  const explanation = policyBlocked
    ? 'The candidate crossed a static safety boundary. It was denied authority and was not delivered.'
    : reasonText[reason ?? ''] ?? 'Evidence was insufficient for automated delivery. A human must decide the next step.';

  return (
    <section
      aria-label="Governance outcome"
      style={{
        marginBottom: '20px',
        padding: '20px',
        borderRadius: '12px',
        border: `1px solid ${accent}55`,
        background: `linear-gradient(135deg, ${accent}14, rgba(12,12,12,0.98))`,
      }}
    >
      <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
        <div style={{ padding: '9px', borderRadius: '9px', background: `${accent}18`, color: accent }}>
          <Icon size={22} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ color: accent, fontSize: '0.72rem', fontWeight: 800, letterSpacing: '0.12em' }}>
            {finalDecision.toUpperCase()}
          </div>
          <h2 style={{ margin: '4px 0 8px', color: '#f8fafc', fontSize: '1.2rem' }}>
            {policyBlocked ? 'Candidate blocked by policy' : 'Human review required'}
          </h2>
          <p style={{ margin: 0, color: 'rgba(226,232,240,0.75)', lineHeight: 1.6 }}>
            {explanation}
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '10px', marginTop: '18px' }}>
        <OutcomeFact icon={<LockKeyhole size={14} />} label="Repository changed" value={repositoryChanged ? 'YES' : 'NO'} />
        <OutcomeFact icon={<GitPullRequest size={14} />} label="Pull request" value="NOT CREATED" />
        <OutcomeFact icon={<Hand size={14} />} label="Attempts used" value={`${attemptsUsed} / ${maxAttempts}`} />
      </div>

      <div style={{ marginTop: '14px', color: 'rgba(226,232,240,0.55)', fontSize: '0.78rem', fontFamily: 'JetBrains Mono, monospace' }}>
        Reason: {reason ?? 'manual_review_required'}
      </div>
    </section>
  );
};

const OutcomeFact: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => (
  <div style={{ border: '1px solid rgba(148,163,184,0.12)', borderRadius: '9px', padding: '11px', background: 'rgba(2,6,23,0.45)' }}>
    <div style={{ display: 'flex', gap: '6px', color: 'rgba(148,163,184,0.6)', fontSize: '0.68rem', textTransform: 'uppercase' }}>
      {icon} {label}
    </div>
    <div style={{ marginTop: '5px', color: '#f8fafc', fontWeight: 750, fontSize: '0.82rem' }}>{value}</div>
  </div>
);

export default FinalDecision;
