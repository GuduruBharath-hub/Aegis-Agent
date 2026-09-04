'use client';

import React from 'react';

interface CardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  headerRight?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  noPadding?: boolean;
  glowColor?: 'gold' | 'amber' | 'none';
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  headerRight,
  footer,
  className,
  style,
  noPadding = false,
  glowColor = 'none',
  onClick,
}) => {
  const glowMap = {
    gold: '0 0 24px rgba(212,175,55,0.2)',
    amber: '0 0 20px rgba(255,191,0,0.15)',
    none: '0 4px 32px rgba(0,0,0,0.8)',
  };

  return (
    <div
      className={className}
      onClick={onClick}
      style={{
        background: 'linear-gradient(135deg, rgba(22,22,22,0.97) 0%, rgba(12,12,12,0.99) 100%)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(212,175,55,0.15)',
        borderRadius: '12px',
        boxShadow: glowMap[glowColor],
        overflow: 'hidden',
        transition: 'all 0.2s ease',
        cursor: onClick ? 'pointer' : 'default',
        ...style,
      }}
    >
      {(title || headerRight) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            borderBottom: '1px solid rgba(212,175,55,0.08)',
          }}
        >
          <div>
            {title && (
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#d4af37', letterSpacing: '0.02em' }}>
                {title}
              </h3>
            )}
            {subtitle && (
              <p style={{ fontSize: '0.78rem', color: 'rgba(212,175,55,0.4)', marginTop: '2px' }}>
                {subtitle}
              </p>
            )}
          </div>
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      <div style={{ padding: noPadding ? 0 : '20px' }}>{children}</div>
      {footer && (
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid rgba(212,175,55,0.08)',
            background: 'rgba(0,0,0,0.4)',
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
};

export default Card;
