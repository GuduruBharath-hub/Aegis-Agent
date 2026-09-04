# Decisions

Append one entry per irreversible or hard-to-revisit choice: what was decided,
why, and what would have to change to revisit it.

## Open

- No open P3-1 decisions. Live access was verified with
  `python -m scripts.verify_feather` on 2026-09-04.

## 2026-09-04 — Featherless Kimi K3 adapter contract (P3-1)

- **Structured output:** Use `response_format={"type":"json_object"}` and
  validate the returned content as `PatchProposal`. Featherless documents
  native tool calling only for Kimi K2 Instruct and Qwen 3, so K3 tool calling
  is not treated as a reliable contract yet. The adapter does not execute any
  model-requested tool.
- **Output budget:** Request 8,000 completion tokens. Featherless's K3 launch
  page says the current serving configuration has a 32K context, while its
  compatibility catalog advertises a larger architecture limit; `/v1/plan`
  can impose a lower account limit. Whole-file transport remains viable for
  the benchmark-sized files, but the live smoke test must confirm acceptance.
- **Response mode:** Use one non-streamed response. A patch event is emitted
  only after the complete response has passed schema validation.
- **Rate limits:** Keep `AEGIS_LLM_CONCURRENCY=1`. Kimi-class requests consume
  four concurrent units and excess capacity is rejected with HTTP 429.
- **Hosting:** Kimi K3 is hosted by Featherless at
  `https://api.featherless.ai/v1`; repository content therefore still requires
  the planned redaction step before real jobs.
- **Sampling:** Send temperature `0` (documented as greedy sampling) and seed
  `0`. Published benchmark results still require repeat runs because backend
  determinism is not guaranteed by the documentation.
- **Model ID:** `moonshotai/Kimi-K3`.
- **Live verification:** The configured Kimi K3 endpoint returned a
  schema-valid `PatchProposal` containing one complete Python file and a bound
  SQL parameter. No repair pass was needed.
- **Sources:** [Kimi K3 launch and model ID](https://featherless.ai/blog/kimi-k3-is-live-on-featherless),
  [chat completions](https://featherless.ai/docs/completions),
  [tool calling](https://featherless.ai/docs/tool-calling),
  [model compatibility](https://featherless.ai/docs/models-model-compatibility),
  [plan limits](https://featherless.ai/docs/api-reference-plan), and
  [concurrency limits](https://featherless.ai/docs/concurrency-limits).

## 2026-09-04 — Retry-prompt verification (P3-4)

- **Decision:** The retry prompt repeats the immutable original context, labels
  the previous candidate as rejected context only, lists every passed gate, and
  includes structured details for each failed gate.
- **Evidence:** `python -m scripts.verify_retry_prompt` seeded a deterministic
  first candidate that parameterized SQL but broke substring matching. Real
  Docker evidence rejected attempt 1. That evidence was then sent to the live
  Kimi K3 adapter, whose new candidate passed on attempt 2 and received the
  gate-issued `verified` decision.
- **Why seed attempt 1:** This makes the rejection beat reproducible instead of
  relying on a capable model to happen to make the intended demonstration
  mistake. The correcting proposal is still generated live by Kimi.

## 2026-09-04 — Sandbox tier (P1-1)

- **Decision:** Use Tier A (Docker) as the sandbox implementation.
- **Evidence:** Docker Desktop reported a healthy Linux/WSL2 engine, and
  `docker run --rm --network none python:3.11-slim python -c "print(1)"`
  completed successfully with output `1` after pulling the image.
- **Why:** The required Python 3.11 image runs with networking disabled, so the
  project can use the stronger process, filesystem, and network isolation model
  specified in §12 instead of the Tier B policy-boundary fallback.
- **Revisit only if:** Docker becomes unavailable on the demo host. Such a run
  must fall back to Tier B and be labelled `subprocess` in the job and UI.

## 2026-09-05 — Preflight probe bounding (P6-2)

- **Decision:** Every preflight probe carries an explicit ceiling, and the total
  budget is *derived* from those ceilings rather than hardcoded.
- **Why:** `httpx` timeouts are per-operation and reset on every byte received,
  so a provider trickling a response can keep a read alive indefinitely. The
  per-operation timeout does not bound the call; only `asyncio.wait_for` around
  the whole probe does. Separately, ten benchmark `git config` reads at the old
  20s ceiling could alone consume 200s.
- **Also:** `--offline` skips the Feather and GitHub probes, so preflight can be
  run repeatedly without spending provider quota, and works on a dead network.
- **Revisit only if:** a probe is added or a timeout raised — the derived budget
  and its regression test must be updated together.
