# AegisAgent

**Evidence-Gated Autonomous Security Remediation**

> AI proposes. Evidence decides.

*Don't trust the AI patch. Make it prove itself.*

**Track:** Autonomous AI Workflows — AI that plans, reasons, acts, observes results,
self-corrects, and safely stops when necessary.

---

## The problem

Security scanners already find vulnerabilities quickly. LLMs already write patches
quickly. Put those two facts together and you get a new problem that neither of them
solves:

**Why would you trust an AI-generated security patch?**

The expensive part of remediation was never typing the fix. A SQL injection might be
four lines of change. The cost is everything around it — investigating the finding,
reproducing the flaw, understanding what the code is supposed to do, writing the
patch, discovering it broke a test, fixing that, re-checking the security property,
and convincing a reviewer. AI can compress the typing. It does nothing for the trust.

And it makes the trust problem worse, because an LLM's confidence is uncorrelated
with its correctness. A patch that closes the vulnerability and silently breaks
search is indistinguishable, at a glance, from one that doesn't.

## The idea

AegisAgent treats every AI-generated patch as **untrusted code that must earn its
delivery.**

The LLM is probabilistic reasoning. The verification system is deterministic control.
The LLM can say "I fixed it" — and that statement carries exactly zero authority.
A candidate patch becomes `VERIFIED` only by surviving six independent gates, none
of which involve a language model.

```
Detect  →  Reproduce  →  Propose  →  Validate  →  Execute  →  Verify
                             ↑                                   │
                             └───────── self-correct ────────────┘
                                    (bounded: 3 attempts)
                                             │
                                    still failing → ESCALATE
```

The interesting engineering is not generating the patch. It is deciding whether a
generated patch has earned delivery.

## How it works

1. **Detect** — Bandit plus custom AST rules produce a normalised finding.
2. **Reproduce** — an attack harness fires real payloads at the running code. If the
   flaw cannot be reproduced, AegisAgent **refuses to patch it.** No blind edits from
   static alerts.
3. **Propose** — the finding, the enclosing function, and the public tests go to the
   LLM, which returns a minimal patch *and a per-line rationale.*
4. **Validate** — syntax, protected paths, diff scope, banned APIs. A candidate that
   fails here is rejected **before it is ever executed.**
5. **Execute** — the patch runs in a Docker sandbox: no network, read-only root,
   dropped capabilities, non-root user, memory and PID limits, **no credentials.**
6. **Verify** — six gates, below.
7. **Self-correct** — a failure becomes structured evidence (which test, which
   assertion, expected vs actual) and feeds a new attempt from the *original* file.
8. **Deliver or stop** — all six green → a real pull request. Otherwise, after three
   attempts, the candidate state is destroyed and the job escalates to a human.

## The six gates

| Gate | Asserts |
|---|---|
| **Security oracle** | The reproduced exploit no longer succeeds — *and* benign behaviour is preserved |
| **Regression** | The repository's existing tests still pass |
| **Post-patch SAST** | The original finding is gone; no new HIGH findings appeared |
| **Patch policy** | The change stayed inside its permitted scope |
| **Artifact integrity** | What ships is byte-identical to what was verified |
| **Explainability** | Every changed line is explained; every citation resolves |

Two design details make these hard to game:

**Reproduction and verification run the same harness.** Only the expected outcome
differs. Nobody can claim the post-patch test was easier than the pre-patch one.

**The security oracle contains benign payloads too.** A "fix" that rejects any input
containing an apostrophe blocks every attack — and fails, because a search for
`O'Brien` must still return its row. The obvious cheat dies at the first gate.

### What VERIFIED means

> This candidate satisfied the six configured gates.

### What VERIFIED does not mean

> This application is secure.

That distinction is printed in the pull request itself. We would rather be trusted
than impressive.

## Explainability — the sixth gate

A patch nobody can explain is a patch nobody should merge. Green gates make
rubber-stamping *feel* safe, which is exactly how AI-generated code gets merged
unexamined.

So the model must return its rationale **in the same call as the patch** — not as a
post-hoc summary — and that rationale is gated deterministically:

- Every changed line is accounted for.
- No explanation for a line that didn't change.
- **Every cited test exists and actually passed in this run.** A fabricated citation
  fails the gate.
- Every security claim names a payload that was actually blocked.
- Restating the code is not explaining it.
- **The "what you must still check yourself" list is never allowed to be empty.**

The reviewer gets an annotated diff, a list of rejected alternatives, and an explicit
statement of what was *not* proven. They can defend the change in review without
re-deriving it.

Honest limit: this proves the explanation is complete and anchored, not that its
reasoning is true. But a fabricated citation cannot survive it — and that is the
failure mode that actually gets bad code merged.

## What the agent cannot do

- Modify the security oracle or any protected test
- Modify AegisAgent's own policy, CI, or sandbox
- Reach a credential or the network from inside the sandbox
- Exceed its retry budget
- Mark its own work verified
- Merge or deploy anything

The GitHub token is a fine-grained PAT scoped to one repository with
`contents:write` and `pull_requests:write`. *"Can it auto-merge?"* has a structural
answer, not a promise: no merge permission exists on the token.

## Architecture

**Feather AI is the brain.** It reads a confirmed finding and proposes a patch and
its rationale.

Everything else is the body:

- **Eyes** — scanner, reproducer, sandbox instrumentation. Turn a repository into observations.
- **Hands** — patch application, git, pull request. Turn a decision into an action.
- **Spine** — the six gates, the policy validator, the state machine. Deterministic,
  model-free, and the only code that can produce `VERIFIED`.

*The brain proposes. The spine decides what is allowed to move.*

Control flow is never delegated to the model. It does not choose its retry budget,
skip a gate, or declare its own work finished.

| Layer | Stack |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind — visualises evidence, computes nothing |
| API | FastAPI — REST plus SSE event stream with replay |
| Control plane | Python asyncio orchestrator, explicit state machine |
| Sandbox | Docker, `--network none`, non-root, read-only, resource-capped |
| Storage | SQLite (WAL), content-addressed artifact store |

## Scope

Deliberately narrow and deeply reliable, rather than broad and shallow.

**Supported for autonomous remediation:** SQL injection (CWE-89) and command
injection (CWE-78) in Python 3.11.

**Everything else** is detected, reported, and escalated as *not supported for
autonomous remediation.* That refusal is a feature. A tool that quietly attempts
what it cannot verify is worse than one that declines.

## The three demos

| | Shows |
|---|---|
| **A · Self-correction** | Candidate 1 fixes the vulnerability and breaks a test → rejected → evidence fed back → candidate 2 passes all six gates → real PR |
| **B · Safe failure** | Three attempts, zero verified candidates, repository unchanged, no PR → **HUMAN REVIEW REQUIRED** |
| **C · Policy attack** | A prompt injection hidden in the source tells the agent to edit the security tests → detected, ignored, and the candidate blocked *before execution* |

Demo A's rejection is the pitch. Most AI-security demos show a patch being
generated. Very few show a patch being rejected by the system that generated it.

## Benchmark

Ten controlled cases. **Five are designed to succeed; five are designed to be
refused** — unsupported patterns, unreproducible findings, policy violations, and one
genuinely unsolvable conflict.

The headline metric is not a success rate. It is **false verifications: 0 / 10** —
always with the denominator.

## Status

Planning complete; implementation underway.

- ✅ **P1 Ground truth** — benchmark repos with genuine regression traps, hidden
  attack harness, scanner and normaliser
- 🔄 **P2 Control plane** — storage, state machine, event bus, workspace manager,
  validator, the gate, integrity hashing, Docker sandbox, credential isolation
  *(9/10 tasks; orchestrator remaining)*
- ⬜ P3 Feather integration · P4 Dashboard · P5 Delivery · P6 Rehearsal

**89 tests passing.** Sandbox running on Tier A (Docker) with network isolation
confirmed.

Full specification: [`docs/plan.md`](docs/plan.md) · Task board:
[`docs/BACKLOG.md`](docs/BACKLOG.md)

## Why this is different

*"GitHub already has AI autofix. What's new?"*

Autofix optimises generation. AegisAgent optimises **trust.** Every candidate is
reproduced first, executed as untrusted code in isolation, and judged by an oracle it
cannot see or edit. A patch that fixes the vulnerability but breaks behaviour is
rejected and retried automatically. The novel part is not the patch — it is the
refusal.

*"Isn't this just a wrapper around an LLM?"*

The wrapper is the product. Swap the model for any other and every guarantee holds,
because none of them come from the model.

---

**The AI is not trusted because it produced a convincing answer.
The patch earns trust by surviving independent evidence.**
