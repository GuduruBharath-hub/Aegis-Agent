import json
from pathlib import Path

from aegis_hidden_tests.command_injection.harness import run as run_command
from aegis_hidden_tests.sql_injection.harness import run as run_sql
from backend.core.workspace import read_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_manifest_defines_ten_runnable_cases_and_six_refusals() -> None:
    manifest = json.loads(read_text(PROJECT_ROOT / "benchmarks" / "MANIFEST.json"))
    cases = manifest["cases"]

    assert len(cases) == 10
    assert len({case["id"] for case in cases}) == 10
    assert all((PROJECT_ROOT / "benchmarks" / case["id"]).is_dir() for case in cases)
    assert sum(case["expected_decision"] != "verified" for case in cases) == 6


def test_refusal_reproduction_fixture_is_not_exploitable() -> None:
    report = run_sql(PROJECT_ROOT / "benchmarks" / "repro_fail")

    assert report.exploited is False
    assert report.benign_preserved is True


def test_both_command_fixtures_are_genuinely_exploitable() -> None:
    assert run_command(PROJECT_ROOT / "benchmarks" / "cmd_basic").exploited is True
    assert run_command(PROJECT_ROOT / "benchmarks" / "cmd_retry").exploited is True
