'use client';

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface SeverityData {
  name: string;
  value: number;
  color: string;
}

interface SecurityOverviewProps {
  data: SeverityData[];
}

/* Custom gradient definitions for 3D-bevel segments */
const GradientDefs: React.FC<{ data: SeverityData[] }> = ({ data }) => (
  <defs>
    {data.map((entry, i) => (
      <linearGradient key={i} id={`sev-grad-${i}`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor={entry.color} stopOpacity={1} />
        <stop offset="100%" stopColor={entry.color} stopOpacity={0.55} />
      </linearGradient>
    ))}
    {/* Outer glow filter */}
    <filter id="donut-glow">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3" />
    </filter>
  </defs>
);

export const SecurityOverview: React.FC<SecurityOverviewProps> = ({ data }) => {
  const total = data.reduce((acc, d) => acc + d.value, 0);

  return (
    <div
      style={{
        background: `
          linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%),
          linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.98) 100%)
        `,
        border: '1px solid rgba(251,191,36,0.1)',
        borderRadius: '14px',
        padding: '22px 20px',
        height: '100%',
        boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 32px rgba(0,0,0,0.5)',
      }}
    >
      <h3
        style={{
          fontSize: '0.82rem',
          fontWeight: 700,
          color: 'rgba(148,163,184,0.7)',
          textTransform: 'uppercase',
          letterSpacing: '0.12em',
          marginBottom: '18px',
        }}
      >
        Severity Distribution
      </h3>

      {/* Donut with gradient segments */}
      <div style={{ width: '100%', height: '170px', position: 'relative' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <GradientDefs data={data} />
            {/* Background glow ring */}
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={46}
              outerRadius={68}
              paddingAngle={3}
              dataKey="value"
              stroke="none"
              style={{ filter: 'url(#donut-glow)', opacity: 0.4 }}
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            {/* Foreground crisp ring with gradient cells */}
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={48}
              outerRadius={72}
              paddingAngle={4}
              dataKey="value"
              stroke="rgba(0,0,0,0.3)"
              strokeWidth={1}
              cornerRadius={3}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={`url(#sev-grad-${i})`} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: 'rgba(15,23,42,0.95)',
                border: '1px solid rgba(251,191,36,0.2)',
                borderRadius: '10px',
                color: '#F8FAFC',
                fontSize: '0.82rem',
                boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                backdropFilter: 'blur(12px)',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>{total}</div>
          <div style={{ fontSize: '0.6rem', color: 'rgba(148,163,184,0.5)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>
            Total
          </div>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '9px', marginTop: '18px' }}>
        {data.map((entry) => (
          <div key={entry.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
              <div
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '3px',
                  background: `linear-gradient(135deg, ${entry.color} 0%, ${entry.color}80 100%)`,
                  boxShadow: `0 0 6px ${entry.color}30`,
                }}
              />
              <span style={{ fontSize: '0.82rem', color: 'rgba(203,213,225,0.7)' }}>{entry.name}</span>
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#F8FAFC' }}>{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SecurityOverview;
