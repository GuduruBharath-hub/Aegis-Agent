'use client';

import React from 'react';

interface ProgressProps {
  value: number;
  max?: number;
  height?: number;
  color?: string;
  showLabel?: boolean;
  label?: string;
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  max = 100,
  height = 6,
  color,
  showLabel = false,
  label,
}) => {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  const barColor = color ?? (pct >= 80 ? '#34D399' : pct >= 50 ? '#FBBF24' : '#F87171');

  return (
    <div>
      {showLabel && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
          {label && <span style={{ fontSize: '0.72rem', color: 'rgba(148,163,184,0.6)' }}>{label}</span>}
          <span style={{ fontSize: '0.72rem', fontWeight: 600, color: barColor }}>{pct.toFixed(0)}%</span>
        </div>
      )}
      <div
        style={{
          width: '100%',
          height: `${height}px`,
          background: 'rgba(248,250,252,0.06)',
          borderRadius: `${height}px`,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${barColor} 0%, ${barColor}aa 100%)`,
            borderRadius: `${height}px`,
            transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: `0 0 8px ${barColor}35`,
          }}
        />
      </div>
    </div>
  );
};

export default Progress;
