# AGENTS.md — AegisAgent

Instructions for any coding agent working in this repository. Read this fully
before your first edit, and re-read the invariants before touching anything
under `backend/validator/`, `backend/verification/`, `backend/sandbox/`, or
`backend/github/`.

## What this project is

AegisAgent detects a vulnerability, reproduces it, asks an LLM (Feather AI) for
a minimal patch, treats that patch as untrusted code, executes it in an isolated
sandbox, and opens a pull request **only** if six independent gates pass.

The specification of record is **`docs/plan.md`**. Tasks reference its section
numbers (§01 … §25). When this file and the plan disagree, this file wins for
process and the plan wins for design; raise the conflict rather than guessing.

The product is not "an LLM that fixes code" — that already exists. The product
is the control plane that decides whether an LLM's patch has earned delivery.
Code that weakens that control plane is wrong even when it makes tests pass.

## Invariants — never violate these

1. **Only `backend/verification/gate.py::evaluate` may produce `VERIFIED`.**
   It is a pure function: no I/O, no network, no clock, no LLM call, no logging
   side effects. Six boolean inputs, one verdict out.
2. **The frontend never computes a verdict.** It renders `job.final_decision`
   from the API. Never derive a verdict from gate booleans in TypeScript.
3. **`aegis_hidden_tests/` never enters a workspace the model can read or
   write.** It is copied into the sandbox as `_aegis_runtime/` *after* policy
   validation, and is excluded from the context builder, the integrity hash
   domain, and the git delivery tree.
4. **Never pass `os.environ` to a subprocess.** The sandbox environment comes
   only from `config.sandbox_env()`, which builds it from a hardcoded allowlist.
   There is a test asserting no key matches `TOKEN|KEY|SECRET|PASSWORD`.
5. **`GITHUB_TOKEN` and `FEATHER_API_KEY` never leave the orchestrator
   process.** GitHub delivery uses the REST API with an `Authorization` header,
   never `git push` with a token in a URL.
6. **All workspace file I/O goes through `workspace.read_text` /
   `write_text`,** which normalise to LF bytes. A single bare `open()` breaks
   the integrity gate on Windows. `core.autocrlf` is `false` here; do not change it.
7. **Policy validation compares the base tree against the candidate tree.**
   Never trust the model's own claim about which files it changed.
8. **The sandbox reports evidence, never verdicts.** Its exit code means "did
   the harness run", never "did the code pass". Verdicts are computed on the
   trusted side from `report.json`.
9. **Retries are bounded by policy.** Never write an unbounded loop around
   patch generation, sandbox execution, or provider calls.
10. **The base workspace is immutable.** Attempt *n* is always `base + patch_n`,
    never the previous candidate plus another patch.
11. **A malformed model response is a technical error, not a failed candidate.**
    It must not consume one of the three patch attempts.
12. **Never weaken a gate, widen a policy limit, or add a path to an allowlist
    to make a test pass.** If a gate blocks legitimate work, say so and stop.

## Working agreement

- Work **one task at a time** from `docs/BACKLOG.md`, in order. Each task has a
  stated done-condition. Do not start the next task until it passes.
- Do not implement future tasks opportunistically "while you're in there".
  A large diff is harder to review than two small ones, and review is the point.
- For anything in `validator/`, `verification/`, or `sandbox/`, write the test
  in the same change as the code. These are the security surface.
- Do not add a dependency that is not already in `requirements.txt` without
  saying why in your summary first.
- Do not create files outside the structure in §03 without saying why.
- If a task turns out to be underspecified, stop and ask. Do not invent a
  design decision and bury it in an implementation.

## Explain your work

Every change you propose must come with, per changed file, a short statement of
**why each non-obvious line is there** — not what it does. The reviewer must be
able to defend this code in review without re-deriving it.

This is not ceremony. It is the same standard §13B applies to AegisAgent's own
output: an unexplained change does not get merged, regardless of who wrote it.

## Commands

```bash
# tests
pytest -q                             # everything
pytest tests/test_gate.py -q          # the exhaustive gate test
pytest tests/test_validator.py -q     # policy surface

# run
uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev            # port 3000

# preflight
python scripts/verify_env.py          # run before any demo
python scripts/run_benchmark.py       # all 10 cases, writes benchmark_runs
```

This machine runs **PowerShell**, not bash. `&&` is not a valid separator in
Windows PowerShell 5.1; use `;` or separate commands. `rm -rf` is
`Remove-Item -Recurse -Force`.

## Style

- Python 3.11 target. Type hints everywhere. `dataclass` for domain objects,
  Pydantic for anything crossing the API boundary.
- No SQL outside `backend/storage/repositories.py`.
- No comments that restate the code. Comment the *why* of a non-obvious choice.
- Structured results, not parsed strings: components return typed objects, and
  the orchestrator never regex-scrapes another component's stdout.
- Async at the orchestrator boundary; plain sync functions inside pure logic.

## Status

Planning complete, implementation not started. See `docs/BACKLOG.md` for the
current task and `docs/plan.md` §21 for the phase gates.
