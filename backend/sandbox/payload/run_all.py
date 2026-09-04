from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
from types import ModuleType


WORKSPACE = Path("/work")
RUNTIME = WORKSPACE / "_aegis_runtime"
OUTPUT = Path("/out")


def _load_harness() -> ModuleType:
    path = RUNTIME / "harness.py"
    spec = importlib.util.spec_from_file_location("_aegis_hidden_harness", path)
    if spec is None or spec.loader is None:
        raise ImportError("hidden harness could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _child_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONPATH": f"{RUNTIME}:{WORKSPACE}",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
        "AEGIS_SANDBOX": "1",
    }


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=WORKSPACE,
        env=_child_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=80,
        check=False,
    )


def _run_attack() -> dict[str, object]:
    harness = _load_harness()
    # Candidate imports may print, but stdout is reserved for the final JSON
    # transport consumed by the trusted control plane.
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        report = harness.run(WORKSPACE)
    value = report.to_dict()
    if not isinstance(value, dict):
        raise TypeError("attack harness did not return an object")
    return value


def _run_pytest() -> dict[str, object]:
    report_path = Path("/tmp/pytest.json")
    _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--json-report",
            f"--json-report-file={report_path}",
        ]
    )
    value = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("pytest report was not an object")
    return value


def _run_bandit() -> dict[str, object]:
    result = _run(
        [
            "bandit",
            "-r",
            ".",
            "-f",
            "json",
            "-x",
            "./_aegis_runtime/*",
        ]
    )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise TypeError("Bandit report was not an object")
    return value


def main() -> int:
    started = perf_counter()

    attack_started = perf_counter()
    attack = _run_attack()
    attack_ms = round((perf_counter() - attack_started) * 1000)

    pytest_started = perf_counter()
    pytest_report = _run_pytest()
    pytest_ms = round((perf_counter() - pytest_started) * 1000)

    bandit_started = perf_counter()
    bandit = _run_bandit()
    bandit_ms = round((perf_counter() - bandit_started) * 1000)

    report: dict[str, object] = {
        "schema": 1,
        "attack": attack,
        "pytest": pytest_report,
        "bandit": bandit,
        "durations": {
            "attack_ms": attack_ms,
            "pytest_ms": pytest_ms,
            "bandit_ms": bandit_ms,
            "total_ms": round((perf_counter() - started) * 1000),
        },
        "python_version": platform.python_version(),
    }
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "report.json").write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
