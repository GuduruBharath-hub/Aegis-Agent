'use client';

import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import type { Patch } from '@/types/finding';

interface PatchViewerProps {
  patch: Patch;
}

export const PatchViewer: React.FC<PatchViewerProps> = ({ patch }) => {
  const [copied, setCopied] = useState(false);
  const [view, setView] = useState<'diff' | 'original' | 'patched'>('diff');

  const handleCopy = async () => {
    await navigator.clipboard.writeText(view === 'original' ? patch.original_code : patch.patched_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderDiff = () => {
    return patch.diff.split('\n').map((line, i) => {
      const isAdd = line.startsWith('+') && !line.startsWith('+++');
      const isRemove = line.startsWith('-') && !line.startsWith('---');
      const isHeader = line.startsWith('@@');
      return (
        <div
          key={i}
          style={{
            background: isAdd ? 'rgba(0,230,118,0.08)' : isRemove ? 'rgba(255,61,113,0.08)' : isHeader ? 'rgba(0,176,255,0.06)' : 'transparent',
            color: isAdd ? '#00e676' : isRemove ? '#ff4d6d' : isHeader ? '#00b0ff' : 'rgba(200,220,255,0.7)',
            padding: '0 12px',
            minHeight: '20px',
            lineHeight: '20px',
            whiteSpace: 'pre',
          }}
        >
          {line || '\u00A0'}
        </div>
      );
    });
  };

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '6px 14px',
    background: active ? 'rgba(0,212,255,0.12)' : 'transparent',
    border: active ? '1px solid rgba(0,212,255,0.25)' : '1px solid transparent',
    borderRadius: '6px',
    color: active ? '#00d4ff' : 'rgba(200,220,255,0.5)',
    cursor: 'pointer',
    fontSize: '0.78rem',
    fontWeight: active ? 600 : 400,
    transition: 'all 0.15s ease',
  });

  return (
    <div
      style={{
        background: 'rgba(2,11,24,0.85)',
        border: '1px solid rgba(0,212,255,0.12)',
        borderRadius: '10px',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          borderBottom: '1px solid rgba(0,212,255,0.08)',
          background: 'rgba(7,20,40,0.5)',
        }}
      >
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={tabStyle(view === 'diff')} onClick={() => setView('diff')}>Diff</button>
          <button style={tabStyle(view === 'original')} onClick={() => setView('original')}>Original</button>
          <button style={tabStyle(view === 'patched')} onClick={() => setView('patched')}>Patched</button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {patch.language && (
            <span style={{ fontSize: '0.72rem', color: 'rgba(200,220,255,0.3)', fontFamily: 'JetBrains Mono, monospace' }}>
              {patch.language}
            </span>
          )}
          <button
            onClick={handleCopy}
            style={{
              background: 'transparent',
              border: 'none',
              color: copied ? '#00e676' : 'rgba(200,220,255,0.4)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.75rem',
              transition: 'color 0.15s ease',
            }}
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Code area */}
      <div
        style={{
          overflowX: 'auto',
          overflowY: 'auto',
          maxHeight: '400px',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.8rem',
          lineHeight: '1.5',
        }}
      >
        {view === 'diff' ? (
          <div style={{ minWidth: 'max-content' }}>{renderDiff()}</div>
        ) : (
          <pre
            style={{
              padding: '16px',
              color: 'rgba(200,220,255,0.75)',
              margin: 0,
              whiteSpace: 'pre',
            }}
          >
            {view === 'original' ? patch.original_code : patch.patched_code}
          </pre>
        )}
      </div>

      {/* Explanation */}
      {patch.explanation && (
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid rgba(0,212,255,0.06)',
            background: 'rgba(0,176,255,0.04)',
          }}
        >
          <div style={{ fontSize: '0.72rem', color: '#00b0ff', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>
            AI Explanation
          </div>
          <p style={{ fontSize: '0.82rem', color: 'rgba(200,220,255,0.6)', lineHeight: 1.5 }}>
            {patch.explanation}
          </p>
        </div>
      )}
    </div>
  );
};

export default PatchViewer;
