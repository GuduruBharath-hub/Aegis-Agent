# Decisions

Append one entry per irreversible or hard-to-revisit choice: what was decided,
why, and what would have to change to revisit it.

## Open

- **Feather API shape (P3-1)** — answer the six questions in plan.md §11.

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
