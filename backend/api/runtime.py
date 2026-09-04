from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Protocol

from backend.agent.feather_client import FeatherPatchModel
from backend.core.config import FeatherSettings, GitHubSettings, RuntimeSettings
from backend.core.event_bus import EventBus
from backend.core.models import BenchmarkRun, Finding, Job
from backend.core.orchestrator import Orchestrator
from backend.core.workspace import WorkspaceManager
from backend.github.client import GitHubClient
from backend.sandbox.runner import SandboxRunner
from backend.scanner.normalizer import scan_repository
from backend.storage.database import Database
from backend.storage.repositories import (
    ArtifactRepo,
    AttemptRepo,
    BenchmarkRunRepo,
    EventRepo,
    FindingRepo,
    JobRepo,
)
from backend.validator.pipeline import ValidatorPipeline, ValidatorPolicy
from backend.verification.pipeline import SandboxCandidateVerifier


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class JobRunner(Protocol):
    async def run(self, job_id: str) -> Job: ...


class RepositoryScanner:
    async def scan(self, workspace: Path) -> tuple[Finding, ...]:
        return await asyncio.to_thread(scan_repository, workspace)


@dataclass(slots=True)
class ApiRuntime:
    connection: sqlite3.Connection
    jobs: JobRepo
    attempts: AttemptRepo
    findings: FindingRepo
    events: EventRepo
    artifacts: ArtifactRepo
    benchmark_runs: BenchmarkRunRepo
    event_bus: EventBus
    runner: JobRunner
    max_attempts: int
    project_root: Path = PROJECT_ROOT
    _tasks: set[asyncio.Task[Job]] = field(
        init=False,
        default_factory=set,
        repr=False,
    )

    @classmethod
    def build_default(cls) -> ApiRuntime:
        runtime_settings = RuntimeSettings()
        database = Database(_from_project(runtime_settings.db_path))
        connection = database.init_db()
        jobs = database.jobs(connection)
        attempts = database.attempts(connection)
        findings = database.findings(connection)
        events = database.events(connection)
        artifacts = database.artifacts(connection)
        benchmark_runs = database.benchmark_runs(connection)
        event_bus = EventBus(events)
        workspace = WorkspaceManager(
            _from_project(runtime_settings.workspace_root)
        )
        validator = ValidatorPipeline(
            ValidatorPolicy.from_file(
                _from_project(runtime_settings.policy_path)
            )
        )
        orchestrator = Orchestrator(
            jobs=jobs,
            attempts=attempts,
            artifacts=artifacts,
            benchmark_runs=benchmark_runs,
            findings=findings,
            events=event_bus,
            workspace=workspace,
            validator=validator,
            scanner=RepositoryScanner(),
            model=FeatherPatchModel(FeatherSettings()),
            verifier=SandboxCandidateVerifier(SandboxRunner(PROJECT_ROOT)),
            delivery=GitHubClient(GitHubSettings()),
            job_wall_clock_seconds=runtime_settings.job_wall_clock_seconds,
        )
        return cls(
            connection=connection,
            jobs=jobs,
            attempts=attempts,
            findings=findings,
            events=events,
            artifacts=artifacts,
            event_bus=event_bus,
            runner=orchestrator,
            max_attempts=runtime_settings.max_attempts,
        )

    def launch(self, job_id: str, *, benchmark_run_id: int | None = None) -> None:
        task = asyncio.create_task(self.runner.run(job_id))
        self._tasks.add(task)
        task.add_done_callback(
            lambda completed: self._task_finished(completed, benchmark_run_id)
        )

    async def close(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self.connection.close()

    def _task_finished(
        self,
        task: asyncio.Task[Job],
        benchmark_run_id: int | None,
    ) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None or benchmark_run_id is None:
            return
        job = task.result()
        run = self.benchmark_runs.get(benchmark_run_id)
        if run is None:
            return
        started = _parse_iso(run.run_at)
        completed = _parse_iso(job.completed_at or job.updated_at)
        actual = job.final_decision or job.state
        self.benchmark_runs.update(
            BenchmarkRun(
                id=run.id,
                case_id=run.case_id,
                job_id=run.job_id,
                expected_decision=run.expected_decision,
                actual_decision=actual,
                attempts_used=job.current_attempt,
                duration_ms=max(0, round((completed - started).total_seconds() * 1000)),
                correct=actual == run.expected_decision,
                run_at=run.run_at,
            )
        )


def _from_project(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)
