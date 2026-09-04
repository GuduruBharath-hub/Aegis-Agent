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

## Status

Planning complete. No implementation yet.

The full engineering plan — architecture, data flow, API contract, database
schema, state machine, security controls, sandbox design, verification and
self-correction implementation, benchmark design, and the phased execution
plan — is in [`docs/plan.html`](docs/plan.html).

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
