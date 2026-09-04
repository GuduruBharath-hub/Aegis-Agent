'use client';

import React, { useState } from 'react';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { BenchmarkCard } from '@/components/benchmarks/BenchmarkCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Progress } from '@/components/ui/Progress';
import { useBenchmarks } from '@/hooks/useBenchmarks';
import { formatRelativeTime } from '@/lib/utils';
import { FlaskConical, TrendingUp, CheckCircle2, XCircle, Clock } from 'lucide-react';

export default function BenchmarksPage() {
    const { scenarios, runs, loading, running, error, triggerRun } = useBenchmarks();
    const [view, setView] = useState<'scenarios' | 'runs'>('scenarios');

    const latestRunMap = runs.reduce<Record<string, (typeof runs)[0]>>((acc, run) => {
        if (!acc[run.scenario_id] || new Date(run.started_at) > new Date(acc[run.scenario_id].started_at)) {
            acc[run.scenario_id] = run;
        }
        return acc;
    }, {});

    const tabBtn = (tab: 'scenarios' | 'runs', label: string) => (
        <button
            onClick={() => setView(tab)}
            style={{
                padding: '8px 18px',
                background: view === tab ? 'rgba(212,175,55,0.1)' : 'transparent',
                border: view === tab ? '1px solid rgba(212,175,55,0.3)' : '1px solid rgba(212,175,55,0.1)',
                borderRadius: '8px',
                color: view === tab ? '#ffd700' : 'rgba(212,175,55,0.45)',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: view === tab ? 600 : 400,
                transition: 'all 0.15s ease',
            }}
        >
            {label}
        </button>
    );

    return (
        <>
            <Header title="Benchmarks" subtitle="Run demo scenarios to test AegisAgent's capabilities" />
            <PageContainer>
                {/* Summary stats */}
                <div className="grid-3" style={{ marginBottom: '24px' }}>
                    {[
                        { label: 'Scenarios Available', value: scenarios.length, icon: <FlaskConical size={16} />, color: '#d4af37' },
                        { label: 'Runs Completed', value: runs.filter((r) => r.status === 'completed').length, icon: <CheckCircle2 size={16} />, color: '#a8e063' },
                        {
                            label: 'Avg Score',
                            value: runs.length > 0
                                ? `${(runs.filter((r) => r.score !== undefined).reduce((a, r) => a + (r.score ?? 0), 0) / Math.max(1, runs.filter((r) => r.score !== undefined).length)).toFixed(1)}%`
                                : '—',
                            icon: <TrendingUp size={16} />,
                            color: '#ffd700',
                        },
                    ].map(({ label, value, icon, color }) => (
                        <div key={label} style={{ background: 'linear-gradient(135deg, rgba(22,22,22,0.97) 0%, rgba(12,12,12,0.99) 100%)', border: '1px solid rgba(212,175,55,0.15)', borderRadius: '10px', padding: '16px', display: 'flex', alignItems: 'center', gap: '14px' }}>
                            <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: `${color}14`, border: `1px solid ${color}28`, display: 'flex', alignItems: 'center', justifyContent: 'center', color, flexShrink: 0 }}>
                                {icon}
                            </div>
                            <div>
                                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffd700' }}>{value}</div>
                                <div style={{ fontSize: '0.72rem', color: 'rgba(212,175,55,0.45)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
                            </div>
                        </div>
                    ))}
                </div>

                <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
                    {tabBtn('scenarios', '🧪 Scenarios')}
                    {tabBtn('runs', '📊 Run History')}
                </div>

                {view === 'scenarios' && (
                    loading ? (
                        <div className="grid-3">
                            {Array.from({ length: 6 }).map((_, i) => (
                                <div key={i} style={{ height: '220px', background: 'rgba(212,175,55,0.03)', borderRadius: '12px', animation: 'pulse-glow 1.5s ease-in-out infinite' }} />
                            ))}
                        </div>
                    ) : error ? (
                        <EmptyState variant="error" title="Failed to load scenarios" description={error} />
                    ) : scenarios.length === 0 ? (
                        <EmptyState title="No benchmark scenarios" description="No scenarios are available from the backend." />
                    ) : (
                        <div className="grid-3">
                            {scenarios.map((scenario) => (
                                <BenchmarkCard
                                    key={scenario.id}
                                    scenario={scenario}
                                    latestRun={latestRunMap[scenario.id]}
                                    onRun={triggerRun}
                                    isRunning={running === scenario.id}
                                />
                            ))}
                        </div>
                    )
                )}

                {view === 'runs' && (
                    <div style={{ background: 'linear-gradient(135deg, rgba(22,22,22,0.97) 0%, rgba(12,12,12,0.99) 100%)', border: '1px solid rgba(212,175,55,0.15)', borderRadius: '12px', overflow: 'hidden' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', padding: '10px 20px', borderBottom: '1px solid rgba(212,175,55,0.08)' }}>
                            {['Scenario', 'Status', 'Score', 'Detection Rate', 'Run Time'].map((col) => (
                                <div key={col} style={{ fontSize: '0.7rem', fontWeight: 700, color: 'rgba(212,175,55,0.45)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{col}</div>
                            ))}
                        </div>

                        {runs.length === 0 ? (
                            <EmptyState title="No runs yet" description="Run a benchmark scenario to see results here." />
                        ) : (
                            runs.map((run) => (
                                <div key={run.id} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', padding: '13px 20px', borderBottom: '1px solid rgba(212,175,55,0.04)', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.875rem', color: 'rgba(255,215,0,0.85)', fontWeight: 500 }}>{run.scenario_name}</span>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        {run.status === 'completed' ? <CheckCircle2 size={13} color="#a8e063" /> : run.status === 'failed' ? <XCircle size={13} color="#ff6060" /> : <Clock size={13} color="#d4af37" />}
                                        <span style={{ fontSize: '0.8rem', color: run.status === 'completed' ? '#a8e063' : run.status === 'failed' ? '#ff6060' : '#ffd700', textTransform: 'capitalize' }}>{run.status}</span>
                                    </div>
                                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffd700' }}>
                                        {run.score !== undefined ? `${run.score.toFixed(1)}%` : '—'}
                                    </span>
                                    <span style={{ fontSize: '0.875rem', color: 'rgba(212,175,55,0.6)' }}>
                                        {(run.detection_rate * 100).toFixed(0)}%
                                    </span>
                                    <span style={{ fontSize: '0.8rem', color: 'rgba(212,175,55,0.35)' }}>
                                        {formatRelativeTime(run.started_at)}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                )}
            </PageContainer>
        </>
    );
}
