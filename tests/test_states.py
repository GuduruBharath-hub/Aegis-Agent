from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from backend.core.models import Job
from backend.core.states import (
    LEGAL,
    TERMINAL,
    FinalDecisionOverwriteError,
    IllegalTransitionError,
    JobState,
    TerminalJobUpdateError,
    validate_transition,
)
from backend.storage.database import Database


def _job(job_id: str = "job_states") -> Job:
    return Job(
        id=job_id,
        repository="org/repo",
        repository_url="https://github.com/org/repo",
        base_sha="abcdef123456",
        mode="demo",
        max_attempts=3,
    )


def test_every_declared_transition_is_accepted() -> None:
    for current, targets in LEGAL.items():
        for target in targets:
            validate_transition(current, target)


def test_every_nonterminal_state_can_fail_on_a_technical_error() -> None:
    for state in JobState:
        if state not in TERMINAL:
            validate_transition(state, JobState.FAILED)


def test_illegal_transition_raises() -> None:
    with pytest.raises(IllegalTransitionError, match="received -> verified"):
        validate_transition(JobState.RECEIVED, JobState.VERIFIED)


@pytest.mark.parametrize("terminal", TERMINAL)
def test_terminal_states_have_no_outgoing_transition(terminal: JobState) -> None:
    with pytest.raises(IllegalTransitionError):
        validate_transition(terminal, JobState.RECEIVED)


def test_repository_accepts_a_legal_transition(tmp_path: Path) -> None:
    db = Database(tmp_path / "legal.db")
    conn = db.init_db()
    try:
        repo = db.jobs(conn)
        current = repo.create(_job())
        proposed = replace(current, state=JobState.SCANNING.value)

        repo.update(proposed)

        persisted = repo.get(current.id)
        assert persisted is not None
        assert persisted.state == JobState.SCANNING.value
    finally:
        conn.close()


def test_repository_rejects_illegal_transition(tmp_path: Path) -> None:
    db = Database(tmp_path / "illegal.db")
    conn = db.init_db()
    try:
        repo = db.jobs(conn)
        current = repo.create(_job())

        with pytest.raises(IllegalTransitionError):
            repo.update(replace(current, state=JobState.VERIFIED.value))

        assert repo.get(current.id) == current
    finally:
        conn.close()


def test_terminal_final_decision_cannot_be_overwritten(tmp_path: Path) -> None:
    db = Database(tmp_path / "terminal.db")
    conn = db.init_db()
    try:
        repo = db.jobs(conn)
        current = repo.create(_job())
        terminal = replace(
            current,
            state=JobState.FAILED.value,
            final_decision="failed",
            final_reason="scanner unavailable",
        )
        repo.update(terminal)

        with pytest.raises(FinalDecisionOverwriteError):
            repo.update(replace(terminal, final_decision=None))
        with pytest.raises(FinalDecisionOverwriteError):
            repo.update(replace(terminal, final_decision="escalated"))

        assert repo.get(current.id) == terminal
    finally:
        conn.close()


def test_terminal_metadata_cannot_be_modified(tmp_path: Path) -> None:
    db = Database(tmp_path / "terminal_metadata.db")
    conn = db.init_db()
    try:
        repo = db.jobs(conn)
        current = repo.create(_job())
        terminal = replace(current, state=JobState.FAILED.value)
        repo.update(terminal)

        with pytest.raises(TerminalJobUpdateError):
            repo.update(replace(terminal, final_reason="late result"))
    finally:
        conn.close()
