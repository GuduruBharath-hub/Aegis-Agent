from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.core.models import Finding
from backend.sandbox.runner import SandboxReport, SandboxRun
from backend.verification.pipeline import SandboxCandidateVerifier


FINDING = Finding(
    id="finding-1",
    scanner="aegis-ast+bandit",
    rule_id="AEGIS-SQL-001",
    category="SQL_INJECTION",
    cwe="CWE-89",
    severity="HIGH",
    confidence="HIGH",
    file_path="app/database.py",
    line_start=8,
    line_end=8,
    symbol="search",
    message="caller input reaches SQL syntax",
)


class StubRunner:
    def __init__(self, run: SandboxRun) -> None:
        self.result = run
        self.ensure_calls = 0

    def ensure_image(self) -> None:
        self.ensure_calls += 1

    def run(self, candidate: Path, *, adapter: str) -> SandboxRun:
        del candidate
        assert adapter == "sql_injection"
        return self.result


def _run(*, failed_test: bool = False, exploited: bool = False) -> SandboxRun:
    outcome = "failed" if failed_test else "passed"
    return SandboxRun(
        tier="docker",
        report=SandboxReport.model_validate(
            {
                "schema": 1,
                "attack": {
                    "exploited": exploited,
                    "benign_preserved": True,
                    "payloads": [
                        {"kind": "attack", "exploited": exploited},
                        {"kind": "benign", "passed": True},
                    ],
                },
                "pytest": {
                    "summary": {
                        "collected": 1,
                        "failed": int(failed_test),
                        "error": 0,
                    },
                    "tests": [
                        {
                            "nodeid": "tests/test_database.py::test_search",
                            "outcome": outcome,
                            "call": {"longrepr": "expected safe result"},
                        }
                    ],
                },
                "bandit": {"results": []},
                "durations": {},
                "python_version": "3.11",
            }
        ),
        exit_code=0,
        stderr="",
        duration_ms=10,
    )


def test_verifier_reports_citable_evidence_without_a_verdict(tmp_path: Path) -> None:
    runner = StubRunner(_run())
    verifier = SandboxCandidateVerifier(runner)  # type: ignore[arg-type]

    reproduced = asyncio.run(verifier.reproduce(tmp_path, FINDING))
    evidence = asyncio.run(verifier.verify(tmp_path, FINDING, 1))

    assert reproduced is False
    assert evidence.security.passed is True
    assert evidence.regression.passed is True
    assert evidence.post_scan.passed is True
    assert evidence.passed_test_ids == (
        "tests/test_database.py::test_search",
    )
    assert evidence.evidence_refs == (
        "security.payload[0]",
        "security.payload[1]",
    )
    assert json.loads(evidence.raw_pytest or "{}")["summary"]["collected"] == 1
    assert json.loads(evidence.raw_bandit or "{}")["results"] == []
    assert json.loads(evidence.raw_harness or "{}")["benign_preserved"] is True
    assert runner.ensure_calls == 1


def test_verifier_preserves_failed_test_evidence(tmp_path: Path) -> None:
    verifier = SandboxCandidateVerifier(StubRunner(_run(failed_test=True)))  # type: ignore[arg-type]

    evidence = asyncio.run(verifier.verify(tmp_path, FINDING, 1))

    assert evidence.regression.passed is False
    assert evidence.passed_test_ids == ()
    assert evidence.regression.detail["failed_tests"] == [
        {
            "test_id": "tests/test_database.py::test_search",
            "outcome": "failed",
            "assertion": "expected safe result",
        }
    ]
