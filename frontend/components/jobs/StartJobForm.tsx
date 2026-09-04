'use client';

import React, { useState } from 'react';
import { Loader2, Send, GitBranch } from 'lucide-react';
import { startJob } from '@/lib/jobs';
import type { Job } from '@/types/job';

interface StartJobFormProps {
  onJobStarted: (job: Job) => void;
  onCancel: () => void;
}

export const StartJobForm: React.FC<StartJobFormProps> = ({ onJobStarted, onCancel }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const job = await startJob({ repo_url: repoUrl.trim(), branch: branch.trim() || 'main' });
      onJobStarted(job);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to start job');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'rgba(2,6,23,0.7)',
    border: '1px solid rgba(251,191,36,0.15)',
    borderRadius: '10px',
    padding: '11px 14px',
    color: '#F8FAFC',
    fontSize: '0.875rem',
    outline: 'none',
    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
    fontFamily: 'JetBrains Mono, monospace',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '0.72rem',
    fontWeight: 700,
    color: 'rgba(148,163,184,0.6)',
    marginBottom: '6px',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
  };

  return (
    <form onSubmit={handleSubmit}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        <div>
          <label style={labelStyle}>Repository URL</label>
          <input
            type="text"
            placeholder="https://github.com/org/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            style={inputStyle}
            autoFocus
          />
        </div>

        <div>
          <label style={labelStyle}>
            <GitBranch size={12} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
            Branch
          </label>
          <input
            type="text"
            placeholder="main"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            style={inputStyle}
          />
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              background: 'rgba(248,113,113,0.08)',
              border: '1px solid rgba(248,113,113,0.18)',
              borderRadius: '10px',
              color: '#FCA5A5',
              fontSize: '0.82rem',
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '6px' }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              padding: '10px 20px',
              background: 'transparent',
              border: '1px solid rgba(148,163,184,0.15)',
              borderRadius: '10px',
              color: 'rgba(203,213,225,0.6)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              transition: 'all 0.15s ease',
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !repoUrl.trim()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 24px',
              background: 'linear-gradient(135deg, rgba(251,191,36,0.2) 0%, rgba(180,83,9,0.1) 100%)',
              border: '1px solid rgba(251,191,36,0.45)',
              borderRadius: '10px',
              color: '#FDE68A',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
              opacity: loading || !repoUrl.trim() ? 0.5 : 1,
              boxShadow: '0 0 16px rgba(251,191,36,0.1)',
              transition: 'all 0.2s ease',
            }}
          >
            {loading ? <Loader2 size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> : <Send size={14} />}
            {loading ? 'Starting...' : 'Start Job'}
          </button>
        </div>
      </div>
    </form>
  );
};

export default StartJobForm;
