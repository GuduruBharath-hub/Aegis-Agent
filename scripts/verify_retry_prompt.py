from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

from backend.agent.feather_client import FeatherPatchModel
from backend.agent.llm_client import (
    PatchFile,
    PatchProposal,
    TechnicalErrorReporter,
)
from backend.core.config import FeatherSettings
from backend.core.event_bus import EventBus
from backend.core.models import (
    CandidateEvidence,
    EvidenceResult,
    FailureEvidence,
    Finding,
    Job,
)
from backend.core.orchestrator import Orchestrator
from backend.core.workspace import WorkspaceManager, read_text
from backend.sandbox.runner import SandboxRunner
from backend.scanner.normalizer import scan_repository
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
REGRESSION_QUERY = '''        rows = active_connection.execute(
            "SELECT id, name, email FROM users WHERE name LIKE ? ORDER BY id",
            (term,),
        ).fetchall()'''


class RepositoryScanner:
    async def scan(self, workspace: Path) -> tuple[Finding, ...]:
        return await asyncio.to_thread(scan_repository, workspace)


class SqlRetryVerifier:
    def __init__(self, runner: SandboxRunner) -> None:
        self.runner = runner

    async def reproduce(self, workspace: Path, finding: Finding) -> bool:
        del finding
        run = await asyncio.to_thread(
            self.runner.run,
            workspace,
            adapter="sql_injection",
        )
        return bool(run.report.attack.get("exploited"))

    async def verify(
        self,
        workspace: Path,
        finding: Finding,
        attempt_number: int,
    ) -> CandidateEvidence:
        del finding, attempt_number
        run = await asyncio.to_thread(
            self.runner.run,
            workspace,
            adapter="sql_injection",
        )
        attack = run.report.attack
        security_passed = (
            not bool(attack.get("exploited"))
            and bool(attack.get("benign_preserved"))
        )
        payloads = attack.get("payloads", [])
        benign_failures = sum(
            1
            for payload in payloads
            if isinstance(payload, dict)
            and payload.get("kind") == "benign"
            and not payload.get("passed")
        )
        attack_failures = sum(
            1
            for payload in payloads
            if isinstance(payload, dict)
            and payload.get("kind") == "attack"
            and payload.get("exploited")
        )

        pytest_report = run.report.pytest
        summary = pytest_report.get("summary", {})
        collected = int(summary.get("collected", 0))
        failed = int(summary.get("failed", 0)) + int(summary.get("error", 0))
        regression_passed = failed == 0 and collected == 18
        failed_tests = []
        for test in pytest_report.get("tests", []):
            if not isinstance(test, dict) or test.get("outcome") == "passed":
                continue
            call = test.get("call", {})
            failed_tests.append(
                {
                    "test_id": test.get("nodeid"),
                    "outcome": test.get("outcome"),
                    "assertion": (
                        call.get("longrepr") if isinstance(call, dict) else None
                    ),
                }
            )

        bandit_results = run.report.bandit.get("results", [])
        sql_findings = [
            result
            for result in bandit_results
            if isinstance(result, dict) and result.get("test_id") == "B608"
        ]
        new_high = [
            result
            for result in bandit_results
            if isinstance(result, dict)
            and result.get("issue_severity") == "HIGH"
        ]
        post_scan_passed = not sql_findings and not new_high

        return CandidateEvidence(
            security=EvidenceResult(
                security_passed,
                "security and benign harness cases passed"
                if security_passed
                else "security or benign harness cases failed",
                {
                    "attack_failures": attack_failures,
                    "benign_failures": benign_failures,
                },
            ),
            regression=EvidenceResult(
                regression_passed,
                "all 18 public tests passed"
                if regression_passed
                else f"{failed} of 18 public tests failed",
                {"failed_tests": failed_tests, "collected": collected},
            ),
            post_scan=EvidenceResult(
                post_scan_passed,
                "original SQL finding absent and no new HIGH finding"
                if post_scan_passed
                else "post-patch scan found a blocking issue",
                {
                    "original_sql_findings": len(sql_findings),
                    "new_high_findings": len(new_high),
                },
            ),
            explain=EvidenceResult(
                True,
                "prompt smoke defers rationale coverage to P3-5",
            ),
        )


@dataclass(slots=True)
class RetryThenFeatherModel:
    feather: FeatherPatchModel
    calls: int = 0

    @property
    def name(self) -> str:
        return self.feather.name

    async def generate_patch(
        self,
        finding: Finding,
        context: str = "",
        policy_summary: str = "",
        failure_evidence: FailureEvidence | None = None,
        report_technical_error: TechnicalErrorReporter | None = None,
    ) -> PatchProposal:
        self.calls += 1
        if self.calls == 1:
            return PatchProposal(
                summary="Bind the search term without preserving wildcards",
                files=(
                    PatchFile(
                        path="app/database.py",
                        new_content=VULNERABLE_SOURCE.replace(
                            VULNERABLE_QUERY,
                            REGRESSION_QUERY,
                        ),
                    ),
                ),
            )
        if failure_evidence is None:
            raise AssertionError("retry call did not receive failure evidence")
        return await self.feather.generate_patch(
            finding,
            context=context,
            policy_summary=policy_summary,
            failure_evidence=failure_evidence,
            report_technical_error=report_technical_error,
        )


async def main() -> None:
    runner = SandboxRunner(PROJECT_ROOT)
    runner.ensure_image()
    with tempfile.TemporaryDirectory(prefix="aegis-retry-smoke-") as temporary:
        root = Path(temporary)
        database = Database(root / "aegis.db")
        connection = database.init_db()
        try:
            jobs = database.jobs(connection)
            attempts = database.attempts(connection)
            events = database.events(connection)
            job = jobs.create(
                Job(
                    id="retry-prompt-smoke",
                    repository="local/sql_retry",
                    repository_url=str(BENCHMARK),
                    base_sha="HEAD",
                    mode="smoke",
                    scenario="sql_retry",
                    max_attempts=3,
                )
            )
            model = RetryThenFeatherModel(
                FeatherPatchModel(FeatherSettings())
            )
            orchestrator = Orchestrator(
                jobs=jobs,
                attempts=attempts,
                findings=database.findings(connection),
                events=EventBus(events),
                workspace=WorkspaceManager(root / ".workspaces"),
                validator=ValidatorPipeline(
                    ValidatorPolicy.from_file(
                        PROJECT_ROOT / "policies" / "security_policy.json"
                    )
                ),
                scanner=RepositoryScanner(),
                model=model,
                verifier=SqlRetryVerifier(runner),
            )
            result = await orchestrator.run(job.id)
            recorded_attempts = attempts.list_for_job(job.id)
            print(
                json.dumps(
                    {
                        "state": result.state,
                        "decision": result.final_decision,
                        "attempts": [
                            {
                                "number": attempt.attempt_number,
                                "decision": attempt.decision,
                                "failure_gate": attempt.failure_gate,
                            }
                            for attempt in recorded_attempts
                        ],
                        "failure_evidence_used": model.calls > 1,
                    },
                    indent=2,
                )
            )
            if result.final_decision != "verified" or len(recorded_attempts) < 2:
                raise SystemExit("retry prompt smoke did not self-correct")
        finally:
            connection.close()


if __name__ == "__main__":
    asyncio.run(main())
