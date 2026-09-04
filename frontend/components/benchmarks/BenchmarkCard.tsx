'use client';

import React from 'react';
import { Play, Loader2, Code2, Tag } from 'lucide-react';
import type { BenchmarkScenario, BenchmarkRun } from '@/lib/benchmarks';

interface BenchmarkCardProps {
  scenario: BenchmarkScenario;
  latestRun?: BenchmarkRun;
  onRun?: (id: string) => void;
  isRunning?: boolean;
}

const difficultyColor: Record<string, string> = {
  easy: '#a8e063',
  medium: '#ffd700',
  hard: '#ff7700',
  expert: '#ff4545',
};

export const BenchmarkCard: React.FC<BenchmarkCardProps> = ({
  scenario,
  latestRun,
  onRun,
  isRunning = false,
}) => {
  return (
    <div
      style={{
        background: 'linear-gradient(135deg, rgba(22,22,22,0.97) 0%, rgba(12,12,12,0.99) 100%)',
        border: '1px solid rgba(212,175,55,0.15)',
        borderRadius: '12px',
        padding: '18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#ffd700', marginBottom: '4px' }}>
            {scenario.name}
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'rgba(212,175,55,0.45)', lineHeight: 1.4 }}>
            {scenario.description}
          </p>
        </div>
        <span
          style={{
            fontSize: '0.72rem',
            fontWeight: 700,
            color: difficultyColor[scenario.difficulty] ?? '#ffd700',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            padding: '3px 8px',
            background: `${difficultyColor[scenario.difficulty] ?? '#ffd700'}15`,
            border: `1px solid ${difficultyColor[scenario.difficulty] ?? '#ffd700'}30`,
            borderRadius: '6px',
            whiteSpace: 'nowrap',
          }}
        >
          {scenario.difficulty}
        </span>
      </div>

      {/* Meta */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem', color: 'rgba(212,175,55,0.4)' }}>
          <Code2 size={12} />
          <span>{scenario.language}</span>
        </div>
        <span style={{ color: 'rgba(212,175,55,0.15)' }}>|</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem', color: 'rgba(212,175,55,0.4)' }}>
          <Tag size={12} />
          <span>{scenario.category}</span>
        </div>
        <span style={{ color: 'rgba(212,175,55,0.15)' }}>|</span>
        <span style={{ fontSize: '0.75rem', color: 'rgba(212,175,55,0.4)' }}>
          Expected: {scenario.expected_decision}
        </span>
      </div>

      {/* Vuln types */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
        {scenario.vulnerability_types.map((vt) => (
          <span
            key={vt}
            style={{
              fontSize: '0.68rem',
              padding: '2px 8px',
              background: 'rgba(212,175,55,0.08)',
              border: '1px solid rgba(212,175,55,0.18)',
              borderRadius: '12px',
              color: 'rgba(212,175,55,0.6)',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {vt}
          </span>
        ))}
      </div>

      {/* Latest run */}
      {latestRun && (
        <div style={{ padding: '10px 12px', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', border: '1px solid rgba(212,175,55,0.08)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.78rem' }}>
            <span style={{ color: 'rgba(212,175,55,0.45)' }}>Last outcome</span>
            <span style={{ color: latestRun.correct === false ? '#ff6060' : '#a8e063', fontWeight: 700 }}>
              {latestRun.actual_decision ?? 'running'}
            </span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'rgba(212,175,55,0.4)' }}>
            Attempts: {latestRun.attempts_used ?? '—'}
          </div>
        </div>
      )}

      {/* Run button */}
      {onRun && (
        <button
          onClick={() => onRun(scenario.id)}
          disabled={isRunning}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '9px',
            background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(180,130,0,0.08))',
            border: '1px solid rgba(212,175,55,0.35)',
            borderRadius: '8px',
            color: '#ffd700',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            fontSize: '0.85rem',
            fontWeight: 600,
            opacity: isRunning ? 0.7 : 1,
            transition: 'all 0.15s ease',
            boxShadow: '0 0 8px rgba(212,175,55,0.1)',
          }}
        >
          {isRunning ? (
            <Loader2 size={14} style={{ animation: 'spin 0.8s linear infinite' }} />
          ) : (
            <Play size={14} />
          )}
          {isRunning ? 'Running...' : 'Run Benchmark'}
        </button>
      )}
    </div>
  );
};

export default BenchmarkCard;
