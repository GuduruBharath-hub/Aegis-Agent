from __future__ import annotations

import asyncio
from dataclasses import replace
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.runtime import ApiRuntime
from backend.core.event_bus import EventBus
from backend.core.models import Attempt, Event, Finding, Job, utcnow_iso
from backend.core.states import JobState
from backend.main import create_app
from backend.storage.database import Database


class CompletingRunner:
    def __init__(self, runtime: ApiRuntime) -> None:
        self.runtime = runtime

    async def run(self, job_id: str) -> Job:
        job = self.runtime.jobs.get(job_id)
        assert job is not None
        await self.runtime.event_bus.publish(
            Event(
                job_id=job.id,
                type="job_created",
                severity="info",
                title="Job accepted",
            )
        )
        states = (
            JobState.SCANNING,
            JobState.FINDING_IDENTIFIED,
            JobState.REPRODUCING,
            JobState.REPRODUCED,
            JobState.CONTEXT_BUILDING,
            JobState.GENERATING_PATCH,
            JobState.VALIDATING_PATCH,
            JobState.SANDBOXING,
            JobState.VERIFYING_SECURITY,
            JobState.VERIFYING_REGRESSION,
            JobState.POST_SCANNING,
            JobState.INTEGRITY_CHECK,
            JobState.VERIFIED,
            JobState.CREATING_PR,
            JobState.COMPLETED,
        )
        for state in states:
            changes: dict[str, object] = {
                "state": state.value,
                "updated_at": utcnow_iso(),
            }
            if state is JobState.VERIFIED:
                changes.update(
                    final_decision="verified",
                    final_reason="all six gates passed",
                )
            if state is JobState.COMPLETED:
                changes["completed_at"] = utcnow_iso()
            job = self.runtime.jobs.update(replace(job, **changes))
            await self.runtime.event_bus.publish(
                Event(
                    job_id=job.id,
                    type="state_changed",
                    severity="success" if state is JobState.COMPLETED else "info",
                    title=f"Job entered {state.value}",
                    data_json=json.dumps({"state": state.value}),
                )
            )
            await asyncio.sleep(0)
        return job


class IdleRunner:
    def __init__(self, runtime: ApiRuntime) -> None:
        self.runtime = runtime

    async def run(self, job_id: str) -> Job:
        job = self.runtime.jobs.get(job_id)
        assert job is not None
        return job


def _runtime(tmp_path: Path) -> ApiRuntime:
    database = Database(tmp_path / "api.db")
    connection = database.init_db()
    event_repo = database.events(connection)
    runtime = ApiRuntime(
        connection=connection,
        jobs=database.jobs(connection),
        attempts=database.attempts(connection),
        findings=database.findings(connection),
        events=event_repo,
        artifacts=database.artifacts(connection),
        event_bus=EventBus(event_repo),
        runner=None,  # type: ignore[arg-type]
        max_attempts=3,
        project_root=tmp_path,
    )
    runtime.runner = CompletingRunner(runtime)
    (tmp_path / "benchmarks" / "sql_retry").mkdir(parents=True)
    return runtime


def test_cli_demo_endpoint_streams_through_verified(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with TestClient(create_app(runtime)) as client:
        response = client.get("/api/demo/sql_retry")
        jobs = client.get("/api/jobs").json()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: state_changed" in response.text
    assert '"state":"completed"' in response.text
    assert jobs[0]["final_decision"] == "verified"
    runtime.connection.close()


def test_post_demo_returns_job_ref_and_attempt_detail(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.runner = IdleRunner(runtime)
    with TestClient(create_app(runtime)) as client:
        started = client.post("/api/demo/sql_retry")
        body = started.json()
        job_id = body["job_id"]
        runtime.attempts.create(
            # The API resolves content-addressed references instead of exposing
            # workspace paths that disappear after candidate cleanup.
            Attempt(
                job_id=job_id,
                attempt_number=1,
                decision="verified",
                model="moonshotai/Kimi-K3",
                diff_ref=runtime.artifacts.put(
                    "unified_diff",
                    "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n",
                ).hash,
                explain_json=json.dumps(
                    {
                        "passed": True,
                        "violations": [],
                        "rationale": {"reviewer_must_confirm": ["review"]},
                    }
                ),
            )
        )
        detail = client.get(f"/api/jobs/{job_id}/attempts/1")

    assert started.status_code == 202
    assert body["stream_url"] == f"/api/jobs/{job_id}/stream"
    assert detail.status_code == 200
    assert detail.json()["gates"]["explain"]["passed"] is True
    assert detail.json()["diff"].endswith("-old\n+new\n")
    assert detail.json()["rationale"]["reviewer_must_confirm"] == ["review"]
    runtime.connection.close()


def test_sse_last_event_id_replays_only_newer_events(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    job = runtime.jobs.create(
        Job(
            id="job_replay",
            repository="fixture",
            repository_url="fixture",
            base_sha="HEAD",
            mode="demo",
            max_attempts=1,
            state="completed",
            final_decision="verified",
        )
    )
    first = runtime.events.create(
        Event(job_id=job.id, type="job_created", severity="info", title="Created")
    )
    final = runtime.events.create(
        Event(
            job_id=job.id,
            type="state_changed",
            severity="success",
            title="Completed",
            data_json='{"state":"completed"}',
        )
    )
    assert first.seq is not None
    assert final.seq is not None

    with TestClient(create_app(runtime)) as client:
        response = client.get(
            f"/api/jobs/{job.id}/stream",
            headers={"Last-Event-ID": str(first.seq)},
        )

    assert f"id: {first.seq}\n" not in response.text
    assert f"id: {final.seq}\n" in response.text
    runtime.connection.close()


def test_sse_query_cursor_bridges_history_to_event_source(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    job = runtime.jobs.create(
        Job(
            id="job_query_replay",
            repository="fixture",
            repository_url="fixture",
            base_sha="HEAD",
            mode="demo",
            max_attempts=1,
            state="completed",
            final_decision="verified",
        )
    )
    first = runtime.events.create(
        Event(job_id=job.id, type="job_created", severity="info", title="Created")
    )
    final = runtime.events.create(
        Event(
            job_id=job.id,
            type="state_changed",
            severity="success",
            title="Completed",
            data_json='{"state":"completed"}',
        )
    )
    assert first.seq is not None
    assert final.seq is not None

    with TestClient(create_app(runtime)) as client:
        response = client.get(
            f"/api/jobs/{job.id}/stream?after={first.seq}",
        )

    assert f"id: {first.seq}\n" not in response.text
    assert f"id: {final.seq}\n" in response.text
    runtime.connection.close()


def test_api_errors_share_one_envelope(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with TestClient(create_app(runtime)) as client:
        missing = client.get("/api/jobs/missing")
        invalid = client.post("/api/jobs", json={"repository_url": ""})

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "job_not_found"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["kind"] == "validation"
    runtime.connection.close()
