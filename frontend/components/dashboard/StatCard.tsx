'use client';

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  accentColor?: string;
  trend?: number;
  trendLabel?: string;
  loading?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  accentColor = '#FBBF24',
  trend,
  trendLabel,
  loading = false,
}) => {
  const hasTrend = trend !== undefined;
  const trendUp = (trend ?? 0) >= 0;

  return (
    <div
      style={{
        /* Card depth – diagonal glass gradient on top of slate base */
        background: `
          linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%),
          linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.98) 100%)
        `,
        border: '1px solid rgba(251,191,36,0.1)',
        borderRadius: '14px',
        padding: '22px 20px',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 32px rgba(0,0,0,0.5)',
        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      {/* Top-right accent radial glow */}
      <div
        style={{
          position: 'absolute',
          top: '-40px',
          right: '-40px',
          width: '140px',
          height: '140px',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${accentColor}14 0%, transparent 70%)`,
          pointerEvents: 'none',
        }}
      />

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <span
          style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            color: 'rgba(148,163,184,0.7)',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
          }}
        >
          {title}
        </span>
        {icon && (
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: `linear-gradient(135deg, ${accentColor}18 0%, ${accentColor}06 100%)`,
              border: `1px solid ${accentColor}22`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: accentColor,
            }}
          >
            {icon}
          </div>
        )}
      </div>

      {/* Value – extremely bright white for maximum contrast */}
      {loading ? (
        <div
          style={{
            height: '38px',
            width: '55%',
            borderRadius: '8px',
            background: 'linear-gradient(90deg, rgba(251,191,36,0.06) 0%, rgba(251,191,36,0.02) 50%, rgba(251,191,36,0.06) 100%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s ease-in-out infinite',
            marginBottom: '8px',
          }}
        />
      ) : (
        <div
          style={{
            fontSize: '2.2rem',
            fontWeight: 800,
            color: '#FFFFFF',
            lineHeight: 1,
            marginBottom: '6px',
            letterSpacing: '-0.02em',
            textShadow: `0 0 40px ${accentColor}30`,
          }}
        >
          {value}
        </div>
      )}

      {/* Subtitle and trend */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {subtitle && (
          <span style={{ fontSize: '0.76rem', color: 'rgba(148,163,184,0.6)' }}>{subtitle}</span>
        )}
        {hasTrend && !loading && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.72rem',
              fontWeight: 600,
              color: trendUp ? '#34D399' : '#FCA5A5',
              padding: '2px 8px',
              borderRadius: '8px',
              background: trendUp ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)',
            }}
          >
            {trendUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {Math.abs(trend!)}%
            {trendLabel && (
              <span style={{ color: 'rgba(148,163,184,0.5)', fontWeight: 400, marginLeft: '2px' }}>
                {trendLabel}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatCard;
