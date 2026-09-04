'use client';

import React from 'react';
import { Lock } from 'lucide-react';

/**
 * The structural limits on the agent. Rendered from a constant rather than
 * from API state on purpose: these are properties of the architecture, not
 * observations about a run, and they hold whether or not a job is in flight.
 */
export const GUARDRAILS: readonly string[] = [
  'Modify the security oracle or any protected test',
  "Modify AegisAgent's own policy, CI, or sandbox",
  'Reach a credential or the network from inside the sandbox',
  'Exceed its retry budget',
  'Mark its own work verified',
  'Bypass a verification gate',
  'Merge or deploy anything',
];

interface GuardrailListProps {
  compact?: boolean;
}

export const GuardrailList: React.FC<GuardrailListProps> = ({ compact = false }) => (
  <section
    style={{
      padding: compact ? '16px 18px' : '22px 24px',
      border: '1px solid rgba(248,113,113,0.18)',
      borderRadius: '14px',
      background: 'linear-gradient(135deg, rgba(127,29,29,0.10), rgba(2,6,23,0.85))',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: '9px', marginBottom: '4px' }}>
      <Lock size={15} color="#FCA5A5" strokeWidth={2.2} />
      <h2
        style={{
          margin: 0,
          color: '#FCA5A5',
          fontSize: compact ? '0.86rem' : '0.98rem',
          fontWeight: 700,
          letterSpacing: '0.01em',
        }}
      >
        What the agent cannot do
      </h2>
    </div>
    <p
      style={{
        margin: '0 0 14px',
        color: 'rgba(203,213,225,0.55)',
        fontSize: '0.76rem',
        lineHeight: 1.5,
      }}
    >
      Enforced by the control plane, not by asking the model nicely.
    </p>
    <ul
      style={{
        listStyle: 'none',
        margin: 0,
        padding: 0,
        display: 'grid',
        gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '7px 20px',
      }}
    >
      {GUARDRAILS.map((item) => (
        <li
          key={item}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '9px',
            color: 'rgba(226,232,240,0.86)',
            fontSize: compact ? '0.76rem' : '0.8rem',
            lineHeight: 1.5,
          }}
        >
          <span
            style={{
              color: '#F87171',
              fontFamily: 'var(--font-geist-mono, monospace)',
              fontSize: '0.8em',
              paddingTop: '2px',
              flexShrink: 0,
            }}
          >
            ✕
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  </section>
);

export default GuardrailList;
