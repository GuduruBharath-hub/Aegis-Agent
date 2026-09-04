'use client';

import React from 'react';
import { Bell, Settings, Activity } from 'lucide-react';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle, actions }) => {
  return (
    <header className="app-header">
      <div style={{ flex: 1 }}>
        {title && (
          <h1
            style={{
              fontSize: '1.1rem',
              fontWeight: 700,
              letterSpacing: '-0.01em',
              background: 'linear-gradient(135deg, #FDE68A 0%, #FBBF24 50%, #B45309 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            {title}
          </h1>
        )}
        {subtitle && (
          <p style={{ fontSize: '0.75rem', color: 'rgba(148,163,184,0.55)', marginTop: '2px', letterSpacing: '0.01em' }}>
            {subtitle}
          </p>
        )}
      </div>

      {actions && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {actions}
        </div>
      )}

      {/* Live pill */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 12px',
          background: 'rgba(52,211,153,0.06)',
          border: '1px solid rgba(52,211,153,0.15)',
          borderRadius: '20px',
          marginLeft: '8px',
        }}
      >
        <Activity size={11} color="#34D399" />
        <span style={{ fontSize: '0.68rem', color: 'rgba(52,211,153,0.8)', fontWeight: 600, letterSpacing: '0.08em' }}>
          LIVE
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '2px', marginLeft: '6px' }}>
        {[Bell, Settings].map((Icon, i) => (
          <button
            key={i}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'rgba(148,163,184,0.4)',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              transition: 'color 0.2s ease',
            }}
          >
            <Icon size={17} />
          </button>
        ))}
      </div>
    </header>
  );
};

export default Header;
