'use client';

import React from 'react';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { GuardrailList } from '@/components/common/GuardrailList';

const AMBER = '#FBBF24';
const MUTED = 'rgba(203,213,225,0.58)';
const MONO = 'var(--font-geist-mono, ui-monospace, monospace)';

const PIPELINE = [
  ['DETECT', 'Bandit + AST rules'],
  ['REPRODUCE', 'real payloads, live code'],
  ['CONTEXT', 'sliced, redacted'],
  ['PATCH', 'model proposes'],
  ['POLICY', 'checked before execution'],
  ['SANDBOX', 'no network, no credentials'],
  ['VERIFY', 'six gates'],
  ['DELIVER', 'pull request'],
] as const;

const GATES = [
  ['Security oracle', 'The reproduced exploit no longer succeeds — and benign behaviour is preserved'],
  ['Regression', "The repository's existing tests still pass"],
  ['Post-patch SAST', 'The original finding is gone; no new HIGH findings appeared'],
  ['Patch policy', 'The change stayed inside its permitted scope'],
  ['Artifact integrity', 'What ships is byte-identical to what was verified'],
  ['Explainability', 'Every changed line is explained; every citation resolves'],
] as const;

const CONTROLS = [
  [
    'Model rewrites the oracle so its patch passes',
    'Hidden tests are injected into the sandbox after policy validation and never enter a model-visible tree',
    'The model can still write code that behaves differently under test — which is why regression also gates',
  ],
  [
    'Model guts the function to block every payload',
    'Regression gate, plus benign payloads inside the security oracle itself',
    'Only as strong as the repository’s existing tests',
  ],
  [
    'Model edits CI, policy, or the sandbox',
    'Protected-path denial on normalised POSIX paths, before execution',
    'Path-normalisation bugs are the classic bypass',
  ],
  [
    'Model introduces exfiltration or code execution',
    'AST denylist on changed files',
    'An early policy filter, not a sound analysis. Containment is the sandbox',
  ],
  [
    'Repository code executes arbitrarily during testing',
    'Docker sandbox: --network none, read-only root, dropped capabilities, non-root, pid/memory caps',
    'Tier B fallback is a policy boundary, not a security boundary — and is labelled as such',
  ],
  [
    'Credential reaches untrusted code',
    'Sandbox environment is constructed from an allowlist, never inherited; delivery uses the REST API',
    'Depends on discipline in one function, so a test asserts it',
  ],
  [
    'Time-of-check / time-of-use at delivery',
    'Three-point tree hashing: after patch, after sandbox, before commit',
    'Guards the window before commit; does not verify the remote after push',
  ],
] as const;

const panel: React.CSSProperties = {
  padding: '22px 24px',
  border: '1px solid rgba(251,191,36,0.16)',
  borderRadius: '14px',
  background: 'linear-gradient(135deg, rgba(251,191,36,0.05), rgba(2,6,23,0.85))',
  marginBottom: '20px',
};

const h2: React.CSSProperties = {
  margin: '0 0 4px',
  color: '#FDE68A',
  fontSize: '0.98rem',
  fontWeight: 700,
};

const sub: React.CSSProperties = {
  margin: '0 0 18px',
  color: MUTED,
  fontSize: '0.78rem',
  lineHeight: 1.5,
};

export default function ArchitecturePage() {
  return (
    <>
      <Header title="Architecture" subtitle="How a proposal becomes evidence" />

      <PageContainer>
        {/* Thesis */}
        <section style={{ ...panel, borderColor: 'rgba(251,191,36,0.26)' }}>
          <h2 style={{ ...h2, fontSize: '1.05rem' }}>AI proposes. Evidence decides.</h2>
          <p style={{ ...sub, marginBottom: 0, maxWidth: '70ch' }}>
            The model is probabilistic reasoning; the verification system is deterministic
            control. A patch becomes <code style={{ color: AMBER, fontFamily: MONO }}>VERIFIED</code>{' '}
            only by surviving six gates, none of which involve a language model. The model has no
            authority over any of them.
          </p>
        </section>

        {/* Pipeline */}
        <section style={panel}>
          <h2 style={h2}>The loop</h2>
          <p style={sub}>
            Eight stages. The arc from VERIFY back to PATCH is the autonomy: a rejected candidate
            becomes structured evidence for the next attempt, bounded at three.
          </p>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px',
              alignItems: 'stretch',
            }}
          >
            {PIPELINE.map(([stage, detail], index) => (
              <React.Fragment key={stage}>
                <div
                  style={{
                    flex: '1 1 150px',
                    minWidth: '150px',
                    padding: '11px 13px',
                    borderRadius: '10px',
                    border: '1px solid rgba(251,191,36,0.2)',
                    background: 'rgba(15,23,42,0.75)',
                  }}
                >
                  <div
                    style={{
                      color: AMBER,
                      fontFamily: MONO,
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      letterSpacing: '0.08em',
                    }}
                  >
                    {stage}
                  </div>
                  <div
                    style={{
                      marginTop: '4px',
                      color: MUTED,
                      fontSize: '0.71rem',
                      lineHeight: 1.4,
                    }}
                  >
                    {detail}
                  </div>
                </div>
                {index < PIPELINE.length - 1 && (
                  <div
                    aria-hidden
                    style={{
                      alignSelf: 'center',
                      color: 'rgba(251,191,36,0.45)',
                      fontFamily: MONO,
                      fontSize: '0.8rem',
                    }}
                  >
                    →
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
          <div
            style={{
              marginTop: '12px',
              padding: '9px 13px',
              borderRadius: '10px',
              border: '1px dashed rgba(251,191,36,0.3)',
              color: 'rgba(253,230,138,0.8)',
              fontFamily: MONO,
              fontSize: '0.72rem',
            }}
          >
            ↺ VERIFY ── failure evidence ──▶ PATCH &nbsp;&nbsp;(attempt 2 of 3, then escalate)
          </div>
        </section>

        {/* Trust boundary */}
        <section style={panel}>
          <h2 style={h2}>Trust boundary</h2>
          <p style={sub}>
            The dividing line is not frontend/backend. It is what may hold a secret and issue a
            verdict, versus what merely runs.
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '14px',
            }}
          >
            {[
              {
                title: 'Trusted control plane',
                colour: '#34D399',
                border: 'rgba(52,211,153,0.28)',
                items: [
                  'FEATHER_API_KEY / GITHUB_TOKEN',
                  'security_policy.json',
                  'aegis_hidden_tests/',
                  'state machine + audit log',
                  'gate.evaluate()  ← the only VERIFIED',
                  'integrity hash comparison',
                ],
              },
              {
                title: 'Untrusted execution plane',
                colour: '#F87171',
                border: 'rgba(248,113,113,0.28)',
                items: [
                  'target repository source',
                  'conftest.py, fixtures, imports',
                  'the model-generated patch',
                  'pytest / bandit processes',
                  'attack harness payloads',
                  '— no tokens, no network —',
                ],
              },
            ].map((side) => (
              <div
                key={side.title}
                style={{
                  padding: '15px 17px',
                  borderRadius: '12px',
                  border: `1px solid ${side.border}`,
                  background: 'rgba(15,23,42,0.7)',
                }}
              >
                <div
                  style={{
                    color: side.colour,
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    letterSpacing: '0.09em',
                    textTransform: 'uppercase',
                    marginBottom: '10px',
                  }}
                >
                  {side.title}
                </div>
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                  {side.items.map((item) => (
                    <li
                      key={item}
                      style={{
                        fontFamily: MONO,
                        fontSize: '0.72rem',
                        lineHeight: 1.85,
                        color: 'rgba(226,232,240,0.82)',
                      }}
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p style={{ ...sub, margin: '12px 0 0', fontSize: '0.75rem' }}>
            Everything crossing right to left is a structured result, never a decision. The sandbox
            reports what happened; only the control plane decides what it means.
          </p>
        </section>

        {/* Gates */}
        <section style={panel}>
          <h2 style={h2}>The six gates</h2>
          <p style={sub}>All six must pass. The gate function is pure: no I/O, no clock, no model.</p>
          <div style={{ display: 'grid', gap: '7px' }}>
            {GATES.map(([name, asserts], index) => (
              <div
                key={name}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '26px 190px 1fr',
                  gap: '12px',
                  alignItems: 'baseline',
                  padding: '10px 13px',
                  borderRadius: '10px',
                  border: '1px solid rgba(148,163,184,0.12)',
                  background: 'rgba(15,23,42,0.6)',
                }}
              >
                <span style={{ color: 'rgba(251,191,36,0.6)', fontFamily: MONO, fontSize: '0.7rem' }}>
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span style={{ color: '#FDE68A', fontSize: '0.8rem', fontWeight: 600 }}>{name}</span>
                <span style={{ color: 'rgba(203,213,225,0.72)', fontSize: '0.77rem', lineHeight: 1.5 }}>
                  {asserts}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Controls, with honest limits */}
        <section style={panel}>
          <h2 style={h2}>Security controls, and their limits</h2>
          <p style={sub}>
            Every control is listed with what it does <em>not</em> cover. A control whose limits are
            undocumented is a control nobody can reason about.
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '620px' }}>
              <thead>
                <tr>
                  {['Threat', 'Control', 'Honest limit'].map((head) => (
                    <th
                      key={head}
                      style={{
                        textAlign: 'left',
                        padding: '8px 12px',
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        letterSpacing: '0.1em',
                        textTransform: 'uppercase',
                        color: 'rgba(203,213,225,0.5)',
                        borderBottom: '1px solid rgba(148,163,184,0.16)',
                      }}
                    >
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {CONTROLS.map(([threat, control, limit]) => (
                  <tr key={threat}>
                    <td style={cell('#FDE68A', 600)}>{threat}</td>
                    <td style={cell('rgba(226,232,240,0.82)')}>{control}</td>
                    <td style={cell('rgba(203,213,225,0.58)')}>{limit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div style={{ marginBottom: '20px' }}>
          <GuardrailList />
        </div>

        {/* Scope */}
        <section
          style={{
            ...panel,
            marginBottom: 0,
            borderColor: 'rgba(148,163,184,0.2)',
            background: 'rgba(15,23,42,0.6)',
          }}
        >
          <h2 style={h2}>What VERIFIED claims</h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '14px',
              marginTop: '12px',
            }}
          >
            <div
              style={{
                padding: '14px 16px',
                borderRadius: '12px',
                border: '1px solid rgba(52,211,153,0.28)',
                background: 'rgba(6,78,59,0.12)',
              }}
            >
              <div style={{ color: '#34D399', fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.09em', marginBottom: '7px' }}>
                IT DOES MEAN
              </div>
              <p style={{ margin: 0, color: 'rgba(226,232,240,0.88)', fontSize: '0.82rem', lineHeight: 1.55 }}>
                This candidate satisfied the six configured gates above, on this commit, with this
                repository&apos;s tests and this oracle&apos;s payloads.
              </p>
            </div>
            <div
              style={{
                padding: '14px 16px',
                borderRadius: '12px',
                border: '1px solid rgba(248,113,113,0.28)',
                background: 'rgba(127,29,29,0.12)',
              }}
            >
              <div style={{ color: '#F87171', fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.09em', marginBottom: '7px' }}>
                IT DOES NOT MEAN
              </div>
              <p style={{ margin: 0, color: 'rgba(226,232,240,0.88)', fontSize: '0.82rem', lineHeight: 1.55 }}>
                The application is secure, or free of vulnerabilities. Evidence is not proof of
                absence, and every pull request says so.
              </p>
            </div>
          </div>
        </section>
      </PageContainer>
    </>
  );
}

function cell(color: string, weight: number = 400): React.CSSProperties {
  return {
    padding: '10px 12px',
    fontSize: '0.77rem',
    lineHeight: 1.5,
    color,
    fontWeight: weight,
    borderBottom: '1px solid rgba(148,163,184,0.08)',
    verticalAlign: 'top',
  };
}
