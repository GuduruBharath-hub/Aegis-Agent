from __future__ import annotations

import shutil
from pathlib import Path

from aegis_hidden_tests.command_injection.harness import run
from backend.core.workspace import read_text, write_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = PROJECT_ROOT / "benchmarks" / "cmd_retry"


def test_command_adapter_detects_vulnerable_fixture() -> None:
    report = run(BENCHMARK)

    assert report.adapter == "command_injection"
    assert report.exploited is True
    assert report.benign_preserved is True


def test_command_adapter_accepts_fixed_fixture(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    shutil.copytree(BENCHMARK, candidate)
    source = read_text(candidate / "app" / "net.py")
    source = source.replace(
        '"ping -c " + str(count) + " " + host,\n        shell=True,',
        '["ping", "-c", str(count), host],\n        shell=False,',
    )
    write_text(candidate / "app" / "net.py", source)

    report = run(candidate)

    assert report.exploited is False
    assert report.benign_preserved is True
    assert all(payload.passed for payload in report.payloads)


def test_command_adapter_exposes_integer_argv_regression(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    shutil.copytree(BENCHMARK, candidate)
    source = read_text(candidate / "app" / "net.py")
    source = source.replace(
        '"ping -c " + str(count) + " " + host,\n        shell=True,',
        '["ping", "-c", count, host],\n        shell=False,',
    )
    write_text(candidate / "app" / "net.py", source)

    report = run(candidate)

    assert report.exploited is False
    assert report.benign_preserved is False
