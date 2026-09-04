from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.runtime import ApiRuntime
from backend.core.event_bus import EventBus
from backend.core.models import Attempt, Event, Finding, Job
from backend.core.replay import ReplayArchive, ReplayError, record_job
from backend.main import create_app
from backend.storage.database import Database


def _runtime(tmp_path: Path, *, regression_passed: bool = True) -> ApiRuntime:
    database = Database(tmp_path / "replay.db")
    connection = database.init_db()
    event_repo = database.events(connection)
    runtime = ApiRuntime(
        connection=connection,
        jobs=database.jobs(connection),
        attempts=database.attempts(connection),
        findings=database.findings(connection),
        events=event_repo,
        artifacts=database.artifacts(connection),
        benchmark_runs=database.benchmark_runs(connection),
        event_bus=EventBus(event_repo),
        runner=None,  # type: ignore[arg-type]
        max_attempts=3,
        project_root=tmp_path,
        replay_archive=ReplayArchive(tmp_path / "replay"),
    )
    job = runtime.jobs.create(
        Job(
            id="job_real_run",
            repository="sql_retry",
            repository_url="benchmarks/sql_retry",
            base_sha="HEAD",
            mode="demo",
            scenario="sql_retry",
            state="completed",
            current_attempt=1,
            max_attempts=3,
            final_decision="verified",
            final_reason="all six gates passed",
        )
    )
    runtime.findings.create(
        Finding(
            id="AEGIS-REPLAY-1",
            scanner="aegis-ast",
            rule_id="AEGIS-SQL-001",
            category="SQL_INJECTION",
            cwe="CWE-89",
            severity="HIGH",
            confidence="HIGH",
            file_path="app/database.py",
            line_start=4,
            line_end=4,
            symbol="search_users",
            message="query text contains untrusted input",
        ),
        job.id,
    )
    diff = runtime.artifacts.put(
        "unified_diff",
        "--- a/app/database.py\n+++ b/app/database.py\n@@ -1 +1 @@\n-old\n+new\n",
    )
    runtime.attempts.create(
        Attempt(
            job_id=job.id,
            attempt_number=1,
            decision="verified",
            diff_ref=diff.hash,
            policy_json=json.dumps({"passed": True, "violations": []}),
            security_json=json.dumps({"passed": True}),
            regression_json=json.dumps({"passed": regression_passed}),
            post_scan_json=json.dumps({"passed": True}),
            integrity_json=json.dumps({"passed": True}),
            explain_json=json.dumps({"passed": True}),
        )
    )
    runtime.events.create(
        Event(
            job_id=job.id,
            type="job_created",
            severity="info",
            title="Job accepted",
        )
    )
    runtime.events.create(
        Event(
            job_id=job.id,
            type="state_changed",
            severity="success",
            title="Job entered completed",
            data_json='{"state":"completed"}',
        )
    )
    return runtime


def _record(runtime: ApiRuntime) -> None:
    record_job(
        "sql-retry-real",
        "job_real_run",
        archive=runtime.replay_archive,
        jobs=runtime.jobs,
        findings=runtime.findings,
        attempts=runtime.attempts,
        events=runtime.events,
        artifacts=runtime.artifacts,
    )


def test_replay_round_trip_restores_evidence_and_marks_mode(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _record(runtime)

    with TestClient(create_app(runtime)) as client:
        available = client.get("/api/replays")
        started = client.post("/api/replays/sql-retry-real")
        replay_job_id = started.json()["job_id"]
        replayed = client.get(f"/api/jobs/{replay_job_id}")
        attempt = client.get(f"/api/jobs/{replay_job_id}/attempts/1")
        stream = client.get(f"/api/jobs/{replay_job_id}/stream")

    assert available.status_code == 200
    assert available.json()[0]["source_job_id"] == "job_real_run"
    assert available.json()[0]["event_count"] == 2
    assert started.status_code == 202
    assert replayed.json()["mode"] == "replay"
    assert replayed.json()["final_decision"] == "verified"
    assert attempt.json()["diff"].endswith("-old\n+new\n")
    assert '"state":"completed"' in stream.text
    runtime.connection.close()


def test_replay_rechecks_six_gates_before_accepting_verified_recording(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path, regression_passed=False)

    with pytest.raises(ReplayError, match="not supported by all six gates"):
        _record(runtime)

    assert not (tmp_path / "replay" / "sql-retry-real.jsonl").exists()
    runtime.connection.close()


def test_replay_rejects_unsafe_recording_ids(tmp_path: Path) -> None:
    archive = ReplayArchive(tmp_path / "replay")

    with pytest.raises(ReplayError, match="unsafe replay recording id"):
        archive.load("../outside")
