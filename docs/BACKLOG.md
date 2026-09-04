# AegisAgent — Implementation Backlog

Work these **in order**, one per agent session. Each task states its
done-condition. Do not start the next task until the current one passes.

Section references (§NN) point at `docs/plan.md`.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## P1 — Ground truth

Prove the vulnerability is real and detectable before writing any agent code.

- [x] **P1-1 · Settle the sandbox tier.** Start Docker Desktop, then run
      `docker run --rm --network none python:3.11-slim python -c "print(1)"`.
      Record the outcome in `docs/DECISIONS.md` as Tier A or Tier B. §12
      **Done when:** `docs/DECISIONS.md` states the tier and the reason.

- [x] **P1-2 · Project skeleton.** Create the `backend/` package tree from §03
      with empty modules and `__init__.py` files, `requirements.txt`,
      `policies/security_policy.json` (§10), `.env.example` (§19).
      **Done when:** `python -c "import backend.main"` succeeds.

- [x] **P1-3 · Benchmark repo `sql_basic`.** A small Flask-free sqlite app with
      `get_user(uid)` built by string concatenation, plus 15–20 real public
      tests in `tests/`. Initialise it as its own git repo. §16
      **Done when:** `pytest` passes inside the fixture, and `git log` shows one commit.

- [x] **P1-4 · Benchmark repo `sql_retry`.** As above, plus `search_users(term)`
      with the `LIKE '%' + term + '%'` trap and a `test_search_partial_match`
      that a naive parameterised fix breaks. §16
      **Done when:** `pytest` passes on the vulnerable code, and hand-applying the
      *naive* fix makes exactly `test_search_partial_match` fail.

- [x] **P1-5 · SQL attack harness.** `aegis_hidden_tests/sql_injection/harness.py`
      with the payload set from §13 including the `O'Brien` benign case.
      **Done when:** it reports `exploited=True` on the vulnerable tree and
      `exploited=False` on a hand-fixed tree. This is the P1 gate.

- [x] **P1-6 · Scanner.** `scanner/bandit_runner.py`, `custom_rules.py` (AST rule
      for concatenated `execute()`), `normalizer.py`. Write these against Bandit's
      *actual* JSON output, not the documented shape. §04
      **Done when:** scanning `sql_retry` yields one normalised `Finding` naming
      `search_users` with `cwe=CWE-89`.

> **P1 GATE:** harness distinguishes vulnerable from fixed, and the scanner
> emits a Finding pointing at the right function.

---

## P2 — Control plane

The whole loop runs end to end with a **stub** brain. No LLM yet.

- [x] **P2-1 · Storage.** SQLite schema from §07, WAL enabled, migrations as
      numbered SQL, `repositories.py` with all SQL confined to it.
      **Done when:** round-trip test creates a job, an attempt and events.

- [x] **P2-2 · State machine.** `states.py` with the enum and the `LEGAL`
      transition table from §08. Illegal transitions raise.
      **Done when:** a test asserts an illegal transition raises, and that a
      terminal `final_decision` cannot be overwritten.

- [x] **P2-3 · Event bus.** Persist-then-publish, global monotonic `seq`,
      per-job `asyncio.Queue`. §09
      **Done when:** a subscriber attaching mid-run receives the full backlog
      followed by live events, with no gap and no duplicate.

- [x] **P2-4 · Workspace manager.** Immutable `base/`, disposable candidates,
      LF-normalised `read_text`/`write_text`. §04
      **Done when:** a test writes a file, commits it via git, checks it out, and
      asserts the content hash is unchanged. **Must pass on Windows.**

- [x] **P2-5 · Validator.** syntax → protected paths → diff scope → AST denylist,
      behind `pipeline.py`. §10, §28-equivalent
      **Done when:** tests cover path escapes (`../`, absolute, backslash), each
      denied import, and each diff limit at boundary and boundary+1.

- [x] **P2-6 · The gate.** `verification/gate.py::evaluate` as a pure function
      over six results. §13, §13B
      **Done when:** an exhaustive test over all 64 boolean combinations asserts
      `verified` is true for exactly one.

- [x] **P2-7 · Integrity.** `tree_hash` with the exclusion set and LF
      normalisation; three-point comparison. §13
      **Done when:** H1/H2/H3 comparison is unit-tested, including a deliberate
      mismatch producing `FAILED` and no delivery.

- [x] **P2-8 · Sandbox runner.** The tier chosen in P1-1, plus `run_all.py`
      writing `report.json`. §12
      **Done when:** running it against `sql_retry` returns a structured report
      containing attack, pytest and bandit results. Exit code is 0 on a failing
      candidate (the harness ran; the candidate lost).

- [x] **P2-9 · Credential isolation test.** §17
      **Done when:** a test asserts `config.sandbox_env()` has no key matching
      `TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL` and no value equal to a set token.

- [x] **P2-10 · StubPatchModel + orchestrator.** Canned candidates: one good, one
      regression-breaking, one protected-file, three consecutive bad. §04, §17
      **Done when:** `pytest tests/test_orchestrator.py` drives all four terminal
      states in seconds with no API key configured. **This is the P2 gate.**

> **P2 GATE:** the entire system works with a fake brain. Do not start P3 until
> this passes — otherwise every later failure has two possible causes.

---

## P3 — Connect the brain (Feather AI)

- [x] **P3-1 · Feather adapter.** `feather_client.py` implementing `PatchModel`.
      Walk the six-question checklist in §11 against Feather's docs first and
      record the answers in `docs/DECISIONS.md`.
      **Done when:** a live call returns a schema-valid `PatchProposal`.

- [x] **P3-2 · Output handling.** extract → validate → repair, with transport
      retries separate from patch attempts. §11, §20
      **Done when:** a test feeds malformed output and asserts a
      `technical_error` event fires and the attempt counter does **not** advance.

- [x] **P3-3 · Context builder + redaction + injection scan.** §23, §24, §25
      **Done when:** context for `sql_retry` contains the enclosing function, its
      imports and the public tests, and no file matching the deny globs.

- [x] **P3-4 · Prompts.** System, task, retry (§11). Iterate the retry prompt
      until it reliably recovers from the wildcard trap.
      **Done when:** `sql_retry` reaches `verified`, having used the failure
      evidence rather than guessing.

- [x] **P3-5 · Rationale + explainability gate.** §13B
      **Done when:** the six coverage checks are tested, including a **fabricated
      test citation**, which must fail the gate.

- [x] **P3-6 · API routes.** jobs, events, stream (SSE with `Last-Event-ID`),
      attempts, demo. §05
      **Done when:** `curl -N /api/demo/sql_retry` streams a complete real run to
      a terminal and ends in `verified`. **This is the P3 gate.**

> **P3 GATE:** a real end-to-end run, driven by Feather, visible in a terminal.
> The project exists at this moment.

---

## P4 — The screen

- [x] **P4-1 · Scaffold + data layer.** Next.js, `lib/api.ts` mirroring the §05
      schemas, `useJobStream` (history then live tail). §06
- [x] **P4-2 · JobHeader, PipelineRail** with the retry arc. §06
- [x] **P4-3 · DiffPane + TimelinePane + AttemptTabs.** §06
- [x] **P4-4 · GateRow** — six cards, raw evidence behind `<details>`. §06
- [ ] **P4-5 · VerdictBanner + GuardrailList.** Renders `final_decision` only. §06
- [ ] **P4-6 · ExplainPane** — click a changed line, see its rationale. §13B

> **P4 GATE:** someone who has not seen the project can narrate what happened
> from the screen alone, including why attempt 1 was rejected. Test on a real person.

---

## P5 — Delivery and refusal

- [ ] **P5-1 · GitHub REST delivery** + H3 comparison. §15
      **Done when:** a real PR exists on a real repository.
- [ ] **P5-2 · PR body** — annotated diff, evidence table, reviewer brief,
      "what was NOT proven". §13B, §15
- [ ] **P5-3 · Command-injection adapter + `cmd_retry` benchmark.** §16
      If this is not mostly a copy of the SQL path, the adapter interface is
      wrong — stop and fix the interface.
- [ ] **P5-4 · Benchmark cases 5–10** and `scripts/run_benchmark.py`. §16
- [ ] **P5-5 · Escalation and policy-block screens** as governance outcomes,
      not errors. §20, §54–55 equivalents

> **P5 GATE:** Demos 1, 2 and 3 launch from the home page and reach their
> expected terminal states. Benchmark reports 0/10 false verifications.

---

## P6 — Freeze and rehearse

- [ ] **P6-1 · Replay mode** with the visible REPLAY badge; record 3 real runs. §16
- [ ] **P6-2 · `scripts/verify_env.py`.** §18
- [ ] **P6-3 · Home page, architecture page, README scope statement.**
- [ ] **P6-4 · Final benchmark run** for the numbers you will quote.
- [ ] **P6-5 · Explain-it-back rehearsal.** §13B
- [ ] **P6-6 · Code freeze**, then three end-to-end demo rehearsals.

> **P6 GATE:** three clean rehearsals. After freeze, any change needs two people
> to agree it is worth the risk.

---

## If you fall behind

Cut from the top of the list in §23. Protect P3-4 above everything else: a
single vulnerability class that reliably demonstrates
detect → reproduce → patch → reject → self-correct → verify beats two classes
that both succeed on the first try.
