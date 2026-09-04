from __future__ import annotations

from pathlib import Path

from backend.sandbox.runner import SandboxRunner
from backend.verification.integrity import tree_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_docker_sql_retry_returns_evidence_even_when_candidate_loses() -> None:
    candidate = PROJECT_ROOT / "benchmarks" / "sql_retry"
    before = tree_hash(candidate)
    runner = SandboxRunner(PROJECT_ROOT)
    runner.ensure_image()

    run = runner.run(candidate, adapter="sql_injection")

    assert run.tier == "docker"
    assert run.exit_code == 0
    assert run.report.schema_version == 1
    assert run.report.attack["exploited"] is True
    assert run.report.pytest["summary"] == {
        "collected": 18,
        "passed": 18,
        "total": 18,
    }
    assert isinstance(run.report.bandit["results"], list)
    assert all(
        "_aegis_runtime" not in finding["filename"]
        for finding in run.report.bandit["results"]
    )
    assert set(run.report.durations) == {
        "attack_ms",
        "pytest_ms",
        "bandit_ms",
        "total_ms",
    }
    assert not (candidate / "_aegis_runtime").exists()
    assert tree_hash(candidate) == before


def test_docker_cmd_retry_uses_command_injection_adapter() -> None:
    candidate = PROJECT_ROOT / "benchmarks" / "cmd_retry"
    before = tree_hash(candidate)
    runner = SandboxRunner(PROJECT_ROOT)
    runner.ensure_image()

    run = runner.run(candidate, adapter="command_injection")

    assert run.exit_code == 0
    assert run.report.attack["adapter"] == "command_injection"
    assert run.report.attack["exploited"] is True
    assert run.report.attack["benign_preserved"] is True
    assert run.report.pytest["summary"]["passed"] == 3
    assert tree_hash(candidate) == before
