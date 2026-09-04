from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from backend.core.models import Artifact, Attempt, Event, Job
from backend.core.workspace import read_text
from backend.storage.database import Database
from backend.storage.repositories import (
    ArtifactRepo,
    AttemptRepo,
    EventRepo,
    JobRepo,
    get_journal_mode,
    is_foreign_keys_enabled,
    list_schema_tables,
    run_migrations,
)


def test_wal_and_foreign_keys_enabled(tmp_path: Path) -> None:
    db_file = tmp_path / "aegis.db"
    db = Database(db_file)
    conn = db.init_db()

    try:
        assert db.check_wal(conn) == "wal"
        assert get_journal_mode(conn) == "wal"

        assert db.check_foreign_keys(conn) is True
        assert is_foreign_keys_enabled(conn) is True
        assert list_schema_tables(conn) == (
            "artifacts",
            "attempts",
            "benchmark_runs",
            "events",
            "findings",
            "jobs",
        )
    finally:
        conn.close()


def test_foreign_key_constraints_enforced(tmp_path: Path) -> None:
    db_file = tmp_path / "aegis_fk.db"
    db = Database(db_file)
    conn = db.init_db()

    attempt_repo = db.attempts(conn)
    event_repo = db.events(conn)

    orphan_attempt = Attempt(
        job_id="non_existent_job",
        attempt_number=1,
        decision="in_progress",
    )
    with pytest.raises(sqlite3.IntegrityError):
        attempt_repo.create(orphan_attempt)

    orphan_event = Event(
        job_id="non_existent_job",
        type="job_created",
        severity="info",
        title="Created",
    )
    with pytest.raises(sqlite3.IntegrityError):
        event_repo.create(orphan_event)

    conn.close()


def test_job_round_trip(tmp_path: Path) -> None:
    db_file = tmp_path / "aegis_jobs.db"
    db = Database(db_file)
    conn = db.init_db()

    job_repo = db.jobs(conn)

    job = Job(
        id="job_test_01",
        repository="org/repo-demo",
        repository_url="https://github.com/org/repo-demo",
        base_sha="abcdef1234567890",
        mode="demo",
        scenario="sql_retry",
        state="scanning",
        current_attempt=0,
        max_attempts=3,
        sandbox_tier="docker",
        final_decision=None,
        final_reason=None,
        branch_name="aegis/fix-test_01",
        pr_url=None,
        pr_number=None,
    )

    created = job_repo.create(job)
    assert created.id == "job_test_01"

    retrieved = job_repo.get("job_test_01")
    assert retrieved is not None
    assert retrieved.id == job.id
    assert retrieved.repository == "org/repo-demo"
    assert retrieved.repository_url == "https://github.com/org/repo-demo"
    assert retrieved.base_sha == "abcdef1234567890"
    assert retrieved.mode == "demo"
    assert retrieved.scenario == "sql_retry"
    assert retrieved.state == "scanning"
    assert retrieved.current_attempt == 0
    assert retrieved.max_attempts == 3
    assert retrieved.sandbox_tier == "docker"
    assert retrieved.final_decision is None
    assert retrieved.created_at == job.created_at
    assert retrieved.updated_at == job.updated_at

    updated_job = Job(
        id=job.id,
        repository=job.repository,
        repository_url=job.repository_url,
        base_sha=job.base_sha,
        mode=job.mode,
        scenario=job.scenario,
        state="finding_identified",
        current_attempt=job.current_attempt,
        max_attempts=job.max_attempts,
        sandbox_tier=job.sandbox_tier,
        branch_name=job.branch_name,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
    job_repo.update(updated_job)

    retrieved_updated = job_repo.get("job_test_01")
    assert retrieved_updated is not None
    assert retrieved_updated.state == "finding_identified"
    assert retrieved_updated.final_decision is None

    jobs = job_repo.list_all()
    assert len(jobs) == 1
    assert jobs[0].id == "job_test_01"

    assert job_repo.get("no_such_job") is None

    conn.close()


def test_attempt_round_trip(tmp_path: Path) -> None:
    db_file = tmp_path / "aegis_attempts.db"
    db = Database(db_file)
    conn = db.init_db()

    job_repo = db.jobs(conn)
    attempt_repo = db.attempts(conn)
    artifact_repo = db.artifacts(conn)

    job = Job(
        id="job_attempt_test",
        repository="org/repo",
        repository_url="https://github.com/org/repo",
        base_sha="1234567890abcdef",
        mode="live",
        max_attempts=3,
    )
    job_repo.create(job)

    diff_content = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-pass\n+return True"
    diff_artifact = artifact_repo.put("diff", diff_content)

    attempt = Attempt(
        job_id=job.id,
        attempt_number=1,
        decision="rejected",
        model="feather",
        prompt_tokens=420,
        completion_tokens=85,
        summary="Naive parameterized query",
        files_changed=1,
        lines_added=1,
        lines_removed=1,
        diff_ref=diff_artifact.hash,
        policy_json='{"passed": true, "violations": []}',
        security_json='{"passed": true, "payloads_blocked": 3}',
        regression_json='{"passed": false, "failures": ["test_partial"]}',
        post_scan_json='{"passed": true, "new_high": 0}',
        integrity_json='{"passed": true}',
        explain_json='{"passed": true, "violations": []}',
        tree_hash_pre="hash_pre_123",
        tree_hash_post="hash_post_123",
        failure_gate="regression",
        failure_reason="test_search_partial_match failed",
        started_at="2026-09-04T12:00:00Z",
        completed_at="2026-09-04T12:00:05Z",
        duration_ms=5120,
    )

    created_attempt = attempt_repo.create(attempt)
    assert created_attempt.job_id == job.id
    assert created_attempt.attempt_number == 1

    retrieved = attempt_repo.get(job.id, 1)
    assert retrieved is not None
    assert retrieved.job_id == job.id
    assert retrieved.attempt_number == 1
    assert retrieved.model == "feather"
    assert retrieved.prompt_tokens == 420
    assert retrieved.completion_tokens == 85
    assert retrieved.summary == "Naive parameterized query"
    assert retrieved.files_changed == 1
    assert retrieved.lines_added == 1
    assert retrieved.lines_removed == 1
    assert retrieved.diff_ref == diff_artifact.hash
    assert retrieved.explain_json == '{"passed": true, "violations": []}'
    assert retrieved.failure_gate == "regression"
    assert retrieved.duration_ms == 5120

    attempt2 = Attempt(
        job_id=job.id,
        attempt_number=2,
        decision="verified",
        model="feather",
        prompt_tokens=510,
        completion_tokens=92,
        summary="Fixed LIKE wildcards correctly",
        files_changed=1,
        lines_added=2,
        lines_removed=2,
        duration_ms=4890,
    )
    attempt_repo.create(attempt2)

    attempts = attempt_repo.list_for_job(job.id)
    assert len(attempts) == 2
    assert attempts[0].attempt_number == 1
    assert attempts[1].attempt_number == 2
    assert attempts[1].decision == "verified"

    assert attempt_repo.get(job.id, 99) is None

    conn.close()


def test_event_round_trip_and_ordering(tmp_path: Path) -> None:
    db_file = tmp_path / "aegis_events.db"
    db = Database(db_file)
    conn = db.init_db()

    job_repo = db.jobs(conn)
    event_repo = db.events(conn)

    job = Job(
        id="job_event_test",
        repository="org/repo",
        repository_url="https://github.com/org/repo",
        base_sha="1234567890abcdef",
        mode="demo",
        max_attempts=3,
    )
    job_repo.create(job)

    ev1 = event_repo.create(
        Event(
            job_id=job.id,
            type="job_created",
            severity="info",
            title="Job initialized",
            message="Remediation job created",
            data_json='{"mode": "demo"}',
        )
    )
    ev2 = event_repo.create(
        Event(
            job_id=job.id,
            type="scan_started",
            severity="info",
            title="AST + Bandit scan started",
            message=None,
        )
    )
    ev3 = event_repo.create(
        Event(
            job_id=job.id,
            type="regression_failed",
            severity="warning",
            title="Regression test failed",
            attempt=1,
            message="1 test failed",
            data_json='{"failed": ["test_search"]}',
        )
    )

    assert ev1.seq is not None
    assert ev2.seq is not None
    assert ev3.seq is not None
    assert ev1.seq < ev2.seq < ev3.seq

    got_ev2 = event_repo.get(ev2.seq)
    assert got_ev2 is not None
    assert got_ev2.seq == ev2.seq
    assert got_ev2.type == "scan_started"
    assert got_ev2.severity == "info"

    all_events = event_repo.list_for_job(job.id)
    assert len(all_events) == 3
    assert [e.seq for e in all_events] == [ev1.seq, ev2.seq, ev3.seq]

    replayed = event_repo.list_for_job(job.id, since_seq=ev1.seq)
    assert len(replayed) == 2
    assert [e.seq for e in replayed] == [ev2.seq, ev3.seq]

    global_replay = event_repo.list_all(since_seq=ev2.seq)
    assert len(global_replay) == 1
    assert global_replay[0].seq == ev3.seq

    conn.close()


def test_cascade_delete_job_removes_attempts_and_events(tmp_path: Path) -> None:
    db_file = tmp_path / "aegis_cascade.db"
    db = Database(db_file)
    conn = db.init_db()

    job_repo = db.jobs(conn)
    attempt_repo = db.attempts(conn)
    event_repo = db.events(conn)

    job = Job(
        id="job_to_delete",
        repository="org/repo",
        repository_url="https://github.com/org/repo",
        base_sha="abcdef",
        mode="demo",
        max_attempts=3,
    )
    job_repo.create(job)

    attempt = Attempt(job_id=job.id, attempt_number=1, decision="verified")
    attempt_repo.create(attempt)

    event = Event(job_id=job.id, type="verified", severity="success", title="Done")
    created_event = event_repo.create(event)

    assert attempt_repo.get(job.id, 1) is not None
    assert event_repo.get(created_event.seq) is not None

    deleted = job_repo.delete(job.id)
    assert deleted is True

    assert attempt_repo.get(job.id, 1) is None
    assert event_repo.get(created_event.seq) is None

    conn.close()


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    db_file = tmp_path / "aegis_mig.db"
    db = Database(db_file)
    conn = db.connect()

    try:
        applied1 = run_migrations(conn)
        assert applied1 == [1, 2]

        applied2 = run_migrations(conn)
        assert applied2 == []
    finally:
        conn.close()


def test_no_sql_outside_repositories() -> None:
    """Enforce AGENTS.md invariant: 'No SQL outside backend/storage/repositories.py'."""
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    repositories_file = (backend_dir / "storage" / "repositories.py").resolve()

    sql_keywords = [
        "SELECT ",
        "INSERT INTO ",
        "UPDATE ",
        "DELETE FROM ",
        "CREATE TABLE ",
        "CREATE INDEX ",
        "PRAGMA ",
    ]

    violations: list[str] = []
    for py_file in backend_dir.rglob("*.py"):
        if py_file.resolve() == repositories_file:
            continue
        content = read_text(py_file).upper()
        for kw in sql_keywords:
            if kw in content:
                violations.append(f"{py_file.relative_to(repo_root)} contains SQL keyword '{kw.strip()}'")

    assert not violations, f"SQL found outside repositories.py:\n" + "\n".join(violations)
