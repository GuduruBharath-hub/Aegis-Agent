'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Briefcase,
  ShieldCheck,
  FlaskConical,
  Network,
  Zap,
  ChevronRight,
} from 'lucide-react';

const navItems = [
  { href: '/',             label: 'Dashboard',    icon: LayoutDashboard },
  { href: '/jobs',         label: 'Jobs',         icon: Briefcase },
  { href: '/remediations', label: 'Remediations', icon: ShieldCheck },
  { href: '/benchmarks',   label: 'Benchmarks',   icon: FlaskConical },
  { href: '/architecture', label: 'Architecture', icon: Network },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <aside className="app-sidebar">
      {/* Logo */}
      <div
        style={{
          padding: '24px 24px 20px',
          borderBottom: '1px solid rgba(251,191,36,0.06)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, rgba(251,191,36,0.2) 0%, rgba(180,83,9,0.1) 100%)',
              border: '1px solid rgba(251,191,36,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(251,191,36,0.15), 0 0 40px rgba(251,191,36,0.05)',
            }}
          >
            <Zap size={18} color="#FBBF24" strokeWidth={2.2} />
          </div>
          <div>
            <div
              style={{
                fontSize: '1rem',
                fontWeight: 800,
                letterSpacing: '0.02em',
                background: 'linear-gradient(135deg, #FDE68A 0%, #FBBF24 50%, #B45309 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              AegisAgent
            </div>
            <div
              style={{
                fontSize: '0.62rem',
                color: 'rgba(251,191,36,0.4)',
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                marginTop: '2px',
                fontWeight: 600,
              }}
            >
              Security AI
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '16px 12px', overflowY: 'auto' }}>
        <div
          style={{
            fontSize: '0.62rem',
            color: 'rgba(148,163,184,0.5)',
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            padding: '4px 14px 10px',
            fontWeight: 700,
          }}
        >
          Navigation
        </div>
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '11px',
                padding: '11px 14px',
                borderRadius: '10px',
                marginBottom: '4px',
                textDecoration: 'none',
                position: 'relative',
                overflow: 'hidden',
                /* Active: soft glowing gradient that fades right */
                color: active ? '#FDE68A' : 'rgba(203,213,225,0.6)',
                background: active
                  ? 'linear-gradient(90deg, rgba(251,191,36,0.14) 0%, rgba(251,191,36,0.04) 60%, transparent 100%)'
                  : 'transparent',
                border: active
                  ? '1px solid rgba(251,191,36,0.18)'
                  : '1px solid transparent',
                boxShadow: active
                  ? '0 0 16px rgba(251,191,36,0.08), inset 0 0 12px rgba(251,191,36,0.03)'
                  : 'none',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                fontSize: '0.875rem',
                fontWeight: active ? 600 : 400,
              }}
            >
              <Icon size={17} strokeWidth={active ? 2.2 : 1.6} />
              <span style={{ flex: 1, letterSpacing: '0.01em' }}>{label}</span>
              {active && (
                <ChevronRight
                  size={13}
                  style={{ opacity: 0.4, color: '#FBBF24' }}
                />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        style={{
          padding: '16px 16px 20px',
          borderTop: '1px solid rgba(251,191,36,0.06)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 14px',
            background: 'linear-gradient(135deg, rgba(251,191,36,0.04) 0%, rgba(251,191,36,0.01) 100%)',
            borderRadius: '10px',
            border: '1px solid rgba(251,191,36,0.08)',
          }}
        >
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#34D399',
              boxShadow: '0 0 8px rgba(52,211,153,0.6)',
              animation: 'breathe 3s ease-in-out infinite',
              flexShrink: 0,
            }}
          />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(248,250,252,0.6)', fontWeight: 500 }}>
              System Online
            </div>
            <div style={{ fontSize: '0.65rem', color: 'rgba(251,191,36,0.35)', marginTop: '1px' }}>
              API Connected
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
