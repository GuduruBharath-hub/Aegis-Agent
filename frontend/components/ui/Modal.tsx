'use client';

import React from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  width?: number;
}

export const Modal: React.FC<ModalProps> = ({ open, onClose, title, children, width = 520 }) => {
  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
    >
      <div
        onClick={onClose}
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(2,6,23,0.85)',
          backdropFilter: 'blur(8px)',
        }}
      />

      <div
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: `${width}px`,
          background: `
            linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%),
            linear-gradient(135deg, rgba(30,41,59,0.97) 0%, rgba(15,23,42,0.99) 100%)
          `,
          border: '1px solid rgba(251,191,36,0.18)',
          borderRadius: '16px',
          boxShadow: '0 24px 80px rgba(0,0,0,0.7), 0 0 40px rgba(251,191,36,0.06)',
          animation: 'fadeIn 0.2s ease forwards',
          overflow: 'hidden',
        }}
      >
        {title && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 24px',
              borderBottom: '1px solid rgba(251,191,36,0.08)',
            }}
          >
            <h2
              style={{
                fontSize: '1rem',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #FDE68A 0%, #FBBF24 60%, #B45309 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              {title}
            </h2>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'rgba(148,163,184,0.5)',
                cursor: 'pointer',
                fontSize: '1.3rem',
                lineHeight: 1,
                padding: '4px',
                transition: 'color 0.15s ease',
              }}
            >
              ×
            </button>
          </div>
        )}

        <div style={{ padding: '22px 24px' }}>{children}</div>
      </div>
    </div>
  );
};

export default Modal;
