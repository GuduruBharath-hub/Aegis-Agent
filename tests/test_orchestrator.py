from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from backend.agent.feather_client import FeatherPatchModel
from backend.agent.llm_client import PatchFile, PatchProposal, StubPatchModel
from backend.core.config import FeatherSettings
from backend.core.event_bus import EventBus
from backend.core.models import (
    Attempt,
    CandidateEvidence,
    EvidenceResult,
    Event,
    Finding,
    Job,
)
from backend.core.orchestrator import Orchestrator
from backend.core.states import JobState
from backend.core.workspace import WorkspaceManager, read_text, write_text
from backend.storage.database import Database
from backend.validator.pipeline import ValidatorPipeline, ValidatorPolicy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = PROJECT_ROOT / "benchmarks" / "sql_retry"
VULNERABLE_SOURCE = read_text(BENCHMARK / "app" / "database.py")
VULNERABLE_QUERY = '''        rows = active_connection.execute(
            "SELECT id, name, email FROM users WHERE name LIKE '%"
            + term
            + "%' ORDER BY id"
        ).fetchall()'''
GOOD_QUERY = '''        rows = active_connection.execute(
            "SELECT id, name, email FROM users WHERE name LIKE ? ORDER BY id",
            (f"%{term}%",),
        ).fetchall()'''
REGRESSION_QUERY = '''        rows = active_connection.execute(
            "SELECT id, name, email FROM users WHERE name LIKE ? ORDER BY id",
            (term,),
        ).fetchall()'''

FINDING = Finding(
    id="AEGIS-STUB-SQL",
    scanner="aegis-ast+bandit",
    rule_id="AEGIS-SQL-001",
    category="SQL_INJECTION",
    cwe="CWE-89",
    severity="HIGH",
    confidence="HIGH",
    file_path="app/database.py",
    line_start=63,
    line_end=67,
    symbol="search_users",
    message="SQL query text includes caller-controlled input",
)


class StaticScanner:
    async def scan(self, workspace: Path) -> tuple[Finding, ...]:
        assert (workspace / FINDING.file_path).is_file()
        return (FINDING,)


class StubVerifier:
    def __init__(self, *, mutate_candidate: bool = False) -> None:
        self.mutate_candidate = mutate_candidate
        self.verify_calls = 0

    async def reproduce(self, workspace: Path, finding: Finding) -> bool:
        assert finding == FINDING
        return VULNERABLE_QUERY in read_text(workspace / finding.file_path)

    async def verify(
        self,
        workspace: Path,
        finding: Finding,
        attempt_number: int,
    ) -> CandidateEvidence:
        del attempt_number
        self.verify_calls += 1
        source = read_text(workspace / finding.file_path)
        if self.mutate_candidate:
            write_text(workspace / "sandbox-mutated.txt", "unexpected mutation\n")

        if GOOD_QUERY in source:
            security = EvidenceResult(True, "attack payloads blocked")
            regression = EvidenceResult(True, "all public tests passed")
            post_scan = EvidenceResult(True, "original finding absent")
        elif REGRESSION_QUERY in source:
            security = EvidenceResult(True, "attack payloads blocked")
            regression = EvidenceResult(
                False,
                "partial matching test failed",
                {
                    "test_id": "tests/test_database.py::test_search_partial_match",
                    "expected": 3,
                    "actual": 0,
                    "failing_call": 'search_users("ali")',
                },
            )
            post_scan = EvidenceResult(True, "original finding absent")
        else:
            security = EvidenceResult(False, "attack remained exploitable")
            regression = EvidenceResult(True, "all public tests passed")
            post_scan = EvidenceResult(False, "original finding remained")
        return CandidateEvidence(
            security=security,
            regression=regression,
            post_scan=post_scan,
            explain=EvidenceResult(True, "stub rationale is complete"),
        )


@dataclass(frozen=True, slots=True)
class RunResult:
    job: Job
    attempts: tuple[Attempt, ...]
    events: tuple[Event, ...]
    model: StubPatchModel | FeatherPatchModel
    verifier: StubVerifier
    job_workspace: Path


def _proposal(summary: str, path: str, content: str) -> PatchProposal:
    return PatchProposal(
        summary=summary,
        files=(PatchFile(path=path, new_content=content),),
    )


GOOD = _proposal(
    "Bind the wildcard search term",
    "app/database.py",
    VULNERABLE_SOURCE.replace(VULNERABLE_QUERY, GOOD_QUERY),
)
REGRESSION = _proposal(
    "Bind the raw search term",
    "app/database.py",
    VULNERABLE_SOURCE.replace(VULNERABLE_QUERY, REGRESSION_QUERY),
)
PROTECTED = _proposal(
    "Change the test fixture",
    "tests/conftest.py",
    read_text(BENCHMARK / "tests" / "conftest.py") + "\n# forbidden edit\n",
)


def _execute(
    tmp_path: Path,
    proposals: tuple[PatchProposal, ...],
    *,
    max_attempts: int,
    mutate_candidate: bool = False,
    model_override: FeatherPatchModel | None = None,
) -> RunResult:
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "aegis.db")
    connection = database.init_db()
    try:
        jobs = database.jobs(connection)
        attempts = database.attempts(connection)
        event_repo = database.events(connection)
        job = jobs.create(
            Job(
                id="job-orchestrator",
                repository="local/sql_retry",
                repository_url=str(BENCHMARK),
                base_sha="HEAD",
                mode="demo",
                scenario="sql_retry",
                max_attempts=max_attempts,
            )
        )
        model = model_override or StubPatchModel(proposals)
        verifier = StubVerifier(mutate_candidate=mutate_candidate)
        workspace_root = tmp_path / ".workspaces"
        orchestrator = Orchestrator(
            jobs=jobs,
            attempts=attempts,
            findings=database.findings(connection),
            events=EventBus(event_repo),
            workspace=WorkspaceManager(workspace_root),
            validator=ValidatorPipeline(
                ValidatorPolicy.from_file(
                    PROJECT_ROOT / "policies" / "security_policy.json"
                )
            ),
            scanner=StaticScanner(),
            model=model,
            verifier=verifier,
        )

        final_job = asyncio.run(orchestrator.run(job.id))
        return RunResult(
            job=final_job,
            attempts=tuple(attempts.list_for_job(job.id)),
            events=tuple(event_repo.list_for_job(job.id)),
            model=model,
            verifier=verifier,
            job_workspace=workspace_root / job.id,
        )
    finally:
        connection.close()


def test_good_stub_candidate_completes_without_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATHER_API_KEY", raising=False)

    result = _execute(tmp_path, (GOOD,), max_attempts=3)

    assert result.job.state == JobState.COMPLETED.value
    assert result.job.final_decision == "verified"
    assert len(result.attempts) == 1
    assert result.attempts[0].decision == "verified"
    assert result.model.calls == [None]
    assert list(result.job_workspace.glob("candidate-*")) == []


def test_regression_evidence_drives_retry_then_good_candidate(
    tmp_path: Path,
) -> None:
    result = _execute(tmp_path, (REGRESSION, GOOD), max_attempts=3)

    assert result.job.state == JobState.COMPLETED.value
    assert [attempt.decision for attempt in result.attempts] == [
        "rejected",
        "verified",
    ]
    retry_evidence = result.model.calls[1]
    assert retry_evidence is not None
    assert retry_evidence.failed_gate == "regression"
    assert retry_evidence.detail["regression"]["test_id"] == (
        "tests/test_database.py::test_search_partial_match"
    )
    assert set(retry_evidence.passed_gates) == {
        "policy",
        "security",
        "post_scan",
        "integrity",
        "explain",
    }


def test_protected_candidate_exhausts_budget_without_sandbox(
    tmp_path: Path,
) -> None:
    result = _execute(tmp_path, (PROTECTED,), max_attempts=1)

    assert result.job.state == JobState.POLICY_REJECTED.value
    assert result.job.final_decision == "policy_rejected"
    assert result.attempts[0].failure_gate == "policy"
    assert result.verifier.verify_calls == 0
    assert "policy_failed" in [event.type for event in result.events]
    assert "sandbox_started" not in [event.type for event in result.events]


def test_three_bad_candidates_escalate_without_delivery(tmp_path: Path) -> None:
    result = _execute(
        tmp_path,
        (REGRESSION, REGRESSION, REGRESSION),
        max_attempts=3,
    )

    assert result.job.state == JobState.ESCALATED.value
    assert result.job.final_decision == "escalated"
    assert result.job.current_attempt == 3
    assert [attempt.failure_gate for attempt in result.attempts] == [
        "regression",
        "regression",
        "regression",
    ]
    assert all(event.type != "verified" for event in result.events)


def test_integrity_mismatch_fails_immediately_and_never_retries(
    tmp_path: Path,
) -> None:
    result = _execute(
        tmp_path,
        (GOOD, GOOD),
        max_attempts=2,
        mutate_candidate=True,
    )

    assert result.job.state == JobState.FAILED.value
    assert result.job.final_decision == "failed"
    assert len(result.attempts) == 1
    assert result.attempts[0].failure_gate == "integrity"
    assert len(result.model.calls) == 1
    assert all(event.type != "verified" for event in result.events)


def test_phase_two_matrix_reaches_all_four_terminal_states(tmp_path: Path) -> None:
    states = {
        _execute(tmp_path / "completed", (GOOD,), max_attempts=1).job.state,
        _execute(tmp_path / "policy", (PROTECTED,), max_attempts=1).job.state,
        _execute(
            tmp_path / "escalated",
            (REGRESSION, REGRESSION, REGRESSION),
            max_attempts=3,
        ).job.state,
        _execute(
            tmp_path / "failed",
            (GOOD,),
            max_attempts=1,
            mutate_candidate=True,
        ).job.state,
    }

    assert states == {
        state.value
        for state in (
            JobState.COMPLETED,
            JobState.ESCALATED,
            JobState.POLICY_REJECTED,
            JobState.FAILED,
        )
    }


def test_malformed_model_output_does_not_advance_patch_attempt(
    tmp_path: Path,
) -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        content = (
            '{"summary": "missing files"}'
            if request_count == 1
            else GOOD.model_dump_json()
        )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
        )

    model = FeatherPatchModel(
        FeatherSettings(
            FEATHER_API_KEY=SecretStr("test-key"),
            AEGIS_LLM_TRANSPORT_RETRIES=2,
        ),
        transport=httpx.MockTransport(handler),
    )

    result = _execute(
        tmp_path,
        (),
        max_attempts=1,
        model_override=model,
    )

    technical_events = [
        event for event in result.events if event.type == "technical_error"
    ]
    assert result.job.state == JobState.COMPLETED.value
    assert result.job.current_attempt == 1
    assert len(result.attempts) == 1
    assert result.attempts[0].attempt_number == 1
    assert request_count == 2
    assert len(technical_events) == 1
    assert technical_events[0].attempt is None
    assert json.loads(technical_events[0].data_json or "{}")["code"] == (
        "malformed_model_output"
    )
