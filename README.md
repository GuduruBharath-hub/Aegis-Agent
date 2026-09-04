# AegisAgent

**Evidence-Gated Autonomous Security Remediation**

> AI proposes. Evidence decides.

AegisAgent reproduces supported Python vulnerabilities, asks an LLM for a minimal
fix, treats that fix as untrusted code, executes it inside an isolated sandbox,
independently verifies it, self-corrects from real failure evidence, and opens a
pull request only after every configured gate passes.

Feather AI is the brain — it proposes patches and their rationale. Everything in
this repository is the body around it: **eyes** (scanner, reproducer, sandbox
instrumentation), **hands** (patch application, git, PR), and a **spine** — the
deterministic gates that are the only code permitted to produce `VERIFIED`.

## Scope of the claim

Read this before reading anything else.

**`VERIFIED` means:** this candidate patch satisfied the six gates below, on
this commit, against this repository's existing tests and this oracle's
payloads.

**`VERIFIED` does not mean:** the application is secure, or free of
vulnerabilities. Evidence is not proof of absence. The same statement appears
in every pull request AegisAgent opens.

Concretely, the limits we know about:

- The security oracle is only as good as the payloads written for it. A finite
  payload set cannot demonstrate the absence of a vulnerability class.
- The regression gate is only as good as the repository's existing tests. On a
  weakly tested repository, a patch that quietly changes behaviour can pass.
- Static analysis is Bandit's ruleset plus our AST rules, not a formal analysis.
- Autonomous remediation covers **SQL injection (CWE-89)** and **command
  injection (CWE-78)** in Python 3.11. Everything else is detected and
  escalated, never patched.
- A finding that cannot be reproduced is never patched, by design.
- The sandbox is a real boundary only on Tier A (Docker). The Tier B fallback
  is a policy boundary, not a security boundary, and every run records which
  tier produced it.

We would rather be trusted than impressive.

## Status

Implementation underway. Planning artefacts:
[`docs/plan.md`](docs/plan.md) is the specification of record,
[`docs/BACKLOG.md`](docs/BACKLOG.md) the task board, and
[`docs/DECISIONS.md`](docs/DECISIONS.md) the log of choices that are expensive
to revisit.

| Phase | State |
|---|---|
| P1 Ground truth | complete |
| P2 Control plane | complete |
| P3 Feather / model chain | complete |
| P4 Dashboard | complete |
| P5 Delivery and refusal | complete |
| P6 Freeze and rehearse | in progress |

Run the preflight before any demo:

```bash
python scripts/verify_env.py --offline
```

## The six gates

A candidate patch becomes `VERIFIED` only when all six pass:

| Gate | Asserts |
|---|---|
| Security oracle | The reproduced exploit no longer succeeds, and benign behaviour is preserved |
| Regression | The repository's existing tests still pass |
| Post-patch SAST | The original finding is gone and no new HIGH findings appear |
| Patch policy | The change stayed inside its permitted scope |
| Artifact integrity | What ships is byte-identical to what was verified |
| Explainability | Every changed line is explained and every citation resolves |

`VERIFIED` means the candidate satisfied these six configured gates. It does not
assert that the application is free of vulnerabilities.

## What the agent cannot do

- Modify the security oracle or any protected test
- Modify AegisAgent's own policy, CI, or sandbox
- Reach a GitHub credential or the network from inside the sandbox
- Exceed its retry budget
- Mark its own work verified
- Merge or deploy anything

## Development notes

`core.autocrlf` is set to `false` for this repository. This is load-bearing, not
cosmetic: the artifact integrity gate compares content hashes across a plain file
copy and a git-managed tree, and CRLF translation would make those hashes differ
on every delivery. See §13 of the plan.
