'use client';

import React, { useState } from 'react';
import type { BenchmarkScenario } from '@/lib/benchmarks';

interface ScenarioSelectorProps {
  scenarios: BenchmarkScenario[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

const categories = ['All', 'OWASP', 'CWE', 'Custom', 'NIST'];

export const ScenarioSelector: React.FC<ScenarioSelectorProps> = ({
  scenarios,
  selectedId,
  onSelect,
}) => {
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [search, setSearch] = useState('');

  const filtered = scenarios.filter((s) => {
    const matchCategory = categoryFilter === 'All' || s.category === categoryFilter;
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase());
    return matchCategory && matchSearch;
  });

  return (
    <div>
      {/* Search */}
      <div style={{ position: 'relative', marginBottom: '12px' }}>
        <input
          type="text"
          placeholder="Search scenarios..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            width: '100%',
            background: 'rgba(2,11,24,0.6)',
            border: '1px solid rgba(0,212,255,0.18)',
            borderRadius: '8px',
            padding: '9px 14px',
            color: '#e8f0fe',
            fontSize: '0.875rem',
            outline: 'none',
          }}
        />
      </div>

      {/* Category filters */}
      <div style={{ display: 'flex', gap: '6px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            style={{
              padding: '4px 12px',
              background: categoryFilter === cat ? 'rgba(0,212,255,0.15)' : 'transparent',
              border: categoryFilter === cat ? '1px solid rgba(0,212,255,0.35)' : '1px solid rgba(0,212,255,0.12)',
              borderRadius: '16px',
              color: categoryFilter === cat ? '#00d4ff' : 'rgba(200,220,255,0.5)',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: categoryFilter === cat ? 600 : 400,
              transition: 'all 0.15s ease',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Scenario list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '340px', overflowY: 'auto' }}>
        {filtered.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'rgba(200,220,255,0.35)', fontSize: '0.875rem' }}>
            No scenarios match your filter.
          </div>
        ) : (
          filtered.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => onSelect(scenario.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 14px',
                background: selectedId === scenario.id ? 'rgba(0,212,255,0.08)' : 'rgba(7,20,40,0.4)',
                border: selectedId === scenario.id ? '1px solid rgba(0,212,255,0.3)' : '1px solid rgba(0,212,255,0.08)',
                borderRadius: '8px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s ease',
              }}
            >
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '2px',
                  background: selectedId === scenario.id ? '#00d4ff' : 'rgba(0,212,255,0.2)',
                  flexShrink: 0,
                }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 500, color: '#e8f0fe' }}>
                  {scenario.name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'rgba(200,220,255,0.4)' }}>
                  {scenario.language} · {scenario.expected_findings} findings
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
};

export default ScenarioSelector;
