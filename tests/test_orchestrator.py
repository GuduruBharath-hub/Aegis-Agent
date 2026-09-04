from __future__ import annotations

import asyncio
from dataclasses import dataclass
from difflib import SequenceMatcher
import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from backend.agent.feather_client import FeatherPatchModel
from backend.agent.llm_client import (
    BehaviourPreservation,
    LineRationale,
    PatchFile,
    PatchProposal,
    PatchRationale,
    RejectedAlternative,
    StubPatchModel,
)
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
from backend.github.client import GitHubDeliveryError, PullRequestResult
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
            passed_test_ids=("tests/test_database.py::test_create_database",),
            evidence_refs=("security.payload[0]",),
            raw_pytest='{"summary":{"collected":1}}',
            raw_bandit='{"results":[]}',
            raw_harness='{"payloads":[]}',
        )


@dataclass(slots=True)
class StubDelivery:
    calls: list[dict[str, object]]

    def __init__(self) -> None:
        self.calls = []

    async def create_pull_request(self, **kwargs: object) -> PullRequestResult:
        self.calls.append(kwargs)
        return PullRequestResult(
            url="https://github.invalid/example/demo/pull/1",
            number=1,
            branch=str(kwargs["branch"]),
        )


class FailingDelivery(StubDelivery):
    async def create_pull_request(self, **kwargs: object) -> PullRequestResult:
        self.calls.append(kwargs)
        raise GitHubDeliveryError("simulated outage")


class MutatingDeliveryWorkspace(WorkspaceManager):
    def prepare_delivery(self, job_id: str, changes: dict[str, str]) -> Path:
        delivery = super().prepare_delivery(job_id, changes)
        write_text(delivery / "delivery-mutation.txt", "unexpected\n")
        return delivery


class HangingPatchModel:
    name = "hanging-model"

    async def generate_patch(self, *args: object, **kwargs: object) -> PatchProposal:
        del args, kwargs
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


@dataclass(frozen=True, slots=True)
class RunResult:
    job: Job
    attempts: tuple[Attempt, ...]
    events: tuple[Event, ...]
    model: StubPatchModel | FeatherPatchModel | HangingPatchModel
    verifier: StubVerifier
    delivery: StubDelivery
    job_workspace: Path


def _proposal(
    summary: str,
    path: str,
    original_content: str,
    content: str,
) -> PatchProposal:
    changed_lines: list[int] = []
    matcher = SequenceMatcher(
        None,
        original_content.splitlines(),
        content.splitlines(),
        autojunk=False,
    )
    for operation, _, _, new_start, new_end in matcher.get_opcodes():
        if operation != "equal":
            changed_lines.extend(range(new_start + 1, new_end + 1))
    return PatchProposal(
        summary=summary,
        strategy="parameterized_query" if path.endswith("database.py") else "other",
        files=(PatchFile(path=path, new_content=content),),
        injection_observed=False,
        rationale=PatchRationale(
            vulnerability_mechanism=(
                "Caller-controlled input becomes executable SQL syntax in this query."
            ),
            fix_mechanism=(
                "A driver-managed binding keeps caller input outside the SQL grammar."
            ),
            line_rationales=(
                LineRationale(
                    path=path,
                    changed_lines=tuple(changed_lines),
                    change_kind=(
                        "parameterize" if path.endswith("database.py") else "other"
                    ),
                    why=(
                        "These changes separate untrusted data from executable query "
                        "syntax while retaining the intended operation."
                    ),
                    earns="security.payload[0]",
                ),
            ),
            behaviour_preservation=(
                BehaviourPreservation(
                    behaviour="database setup remains operational",
                    preserved_by="the patch leaves database creation unchanged",
                    proven_by="tests/test_database.py::test_create_database",
                ),
            ),
            rejected_alternatives=(
                RejectedAlternative(
                    approach="strip punctuation from input",
                    why_not="that would reject legitimate user data",
                ),
            ),
            residual_risk=("Other call sites require independent review.",),
            reviewer_must_confirm=("Confirm the bound value keeps expected semantics.",),
        ),
    )


GOOD = _proposal(
    "Bind the wildcard search term",
    "app/database.py",
    VULNERABLE_SOURCE,
    VULNERABLE_SOURCE.replace(VULNERABLE_QUERY, GOOD_QUERY),
)
REGRESSION = _proposal(
    "Bind the raw search term",
    "app/database.py",
    VULNERABLE_SOURCE,
    VULNERABLE_SOURCE.replace(VULNERABLE_QUERY, REGRESSION_QUERY),
)
PROTECTED = _proposal(
    "Change the test fixture",
    "tests/conftest.py",
    read_text(BENCHMARK / "tests" / "conftest.py"),
    read_text(BENCHMARK / "tests" / "conftest.py") + "\n# forbidden edit\n",
)


def _execute(
    tmp_path: Path,
    proposals: tuple[PatchProposal, ...],
    *,
    max_attempts: int,
    mutate_candidate: bool = False,
    mutate_delivery: bool = False,
    model_override: FeatherPatchModel | HangingPatchModel | None = None,
    delivery_override: StubDelivery | None = None,
    job_wall_clock_seconds: float = 480.0,
) -> RunResult:
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "aegis.db")
    connection = database.init_db()
    try:
        jobs = database.jobs(connection)
        attempts = database.attempts(connection)
        artifacts = database.artifacts(connection)
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
        delivery = delivery_override or StubDelivery()
        workspace_root = tmp_path / ".workspaces"
        workspace_type = MutatingDeliveryWorkspace if mutate_delivery else WorkspaceManager
        orchestrator = Orchestrator(
            jobs=jobs,
            attempts=attempts,
            artifacts=artifacts,
            findings=database.findings(connection),
            events=EventBus(event_repo),
            workspace=workspace_type(workspace_root),
            validator=ValidatorPipeline(
                ValidatorPolicy.from_file(
                    PROJECT_ROOT / "policies" / "security_policy.json"
                )
            ),
            scanner=StaticScanner(),
            model=model,
            verifier=verifier,
            delivery=delivery,
            job_wall_clock_seconds=job_wall_clock_seconds,
        )

        final_job = asyncio.run(orchestrator.run(job.id))
        return RunResult(
            job=final_job,
            attempts=tuple(attempts.list_for_job(job.id)),
            events=tuple(event_repo.list_for_job(job.id)),
            model=model,
            verifier=verifier,
            delivery=delivery,
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
    assert result.job.pr_url == "https://github.invalid/example/demo/pull/1"
    assert result.job.pr_number == 1
    assert result.job.branch_name == "aegis/aegis-stub-sql-cwe-89"
    assert result.delivery.calls[0]["expected_base_sha"] == result.job.base_sha
    assert result.delivery.calls[0]["files"] == {
        "app/database.py": GOOD.files[0].new_content
    }
    pr_body = str(result.delivery.calls[0]["body"])
    assert "### Evidence" in pr_body
    assert "### Annotated diff" in pr_body
    assert "### Reviewer brief" in pr_body
    assert "### What was NOT proven" in pr_body
    assert "**This PR requires human review. AegisAgent cannot merge it.**" in pr_body
    assert result.attempts[0].diff_ref is not None
    assert result.attempts[0].pytest_ref is not None
    assert result.attempts[0].bandit_ref is not None
    assert result.attempts[0].harness_ref is not None
    database = Database(tmp_path / "aegis.db")
    connection = database.connect()
    artifact = database.artifacts(connection).get(result.attempts[0].diff_ref)
    connection.close()
    assert artifact is not None
    assert "-            + term" in artifact.content
    assert "+            (f\"%{term}%\",)," in artifact.content
    assert json.loads(result.attempts[0].explain_json or "{}")["passed"] is True
    assert result.model.calls == [None]
    assert list(result.job_workspace.glob("candidate-*")) == []
    assert not (result.job_workspace / "delivery").exists()
    pr_event = next(event for event in result.events if event.type == "pr_created")
    assert json.loads(pr_event.data_json or "{}")["delivery_hash"] == (
        result.attempts[0].tree_hash_pre
    )


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


def test_fabricated_rationale_citation_blocks_verified(tmp_path: Path) -> None:
    fabricated_claim = GOOD.rationale.behaviour_preservation[0].model_copy(
        update={"proven_by": "tests/test_database.py::test_does_not_exist"}
    )
    proposal = GOOD.model_copy(
        update={
            "rationale": GOOD.rationale.model_copy(
                update={"behaviour_preservation": (fabricated_claim,)}
            )
        }
    )

    result = _execute(tmp_path, (proposal,), max_attempts=1)

    assert result.job.state == JobState.ESCALATED.value
    assert result.attempts[0].failure_gate == "explain"
    explanation = json.loads(result.attempts[0].explain_json or "{}")
    assert explanation["passed"] is False
    assert [item["code"] for item in explanation["violations"]] == [
        "uncitable_test"
    ]
    assert all(event.type != "verified" for event in result.events)


def test_protected_candidate_exhausts_budget_without_sandbox(
    tmp_path: Path,
) -> None:
    result = _execute(tmp_path, (PROTECTED,), max_attempts=1)

    assert result.job.state == JobState.POLICY_REJECTED.value
    assert result.job.final_decision == "policy_rejected"
    assert result.attempts[0].failure_gate == "policy"
    assert result.attempts[0].diff_ref is not None
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


def test_delivery_hash_mismatch_fails_without_calling_github(tmp_path: Path) -> None:
    result = _execute(
        tmp_path,
        (GOOD,),
        max_attempts=1,
        mutate_delivery=True,
    )

    assert result.job.state == JobState.FAILED.value
    assert result.job.final_decision == "verified"
    assert result.delivery.calls == []
    assert "delivery_integrity_failed" in [event.type for event in result.events]
    assert not (result.job_workspace / "delivery").exists()


def test_github_failure_preserves_verified_decision(tmp_path: Path) -> None:
    delivery = FailingDelivery()
    result = _execute(
        tmp_path,
        (GOOD,),
        max_attempts=1,
        delivery_override=delivery,
    )

    assert result.job.state == JobState.FAILED.value
    assert result.job.final_decision == "verified"
    assert result.job.pr_url is None
    assert len(delivery.calls) == 1
    assert "technical_error" in [event.type for event in result.events]


def test_job_wall_clock_timeout_is_technical_and_consumes_no_attempt(
    tmp_path: Path,
) -> None:
    result = _execute(
        tmp_path,
        (),
        max_attempts=3,
        model_override=HangingPatchModel(),
        job_wall_clock_seconds=0.05,
    )

    assert result.job.state == JobState.FAILED.value
    assert result.job.final_decision == "failed"
    assert result.job.final_reason == "job_wall_clock_timeout"
    assert result.job.current_attempt == 0
    assert result.attempts == ()
    error = next(event for event in result.events if event.type == "technical_error")
    assert json.loads(error.data_json or "{}") == {
        "code": "job_wall_clock_timeout",
        "component": "orchestrator",
        "limit_seconds": 0.05,
    }


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
