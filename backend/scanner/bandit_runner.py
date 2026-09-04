from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import tempfile


class BanditOutputError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BanditScan:
    results: tuple[dict[str, object], ...]
    errors: tuple[object, ...]
    stdout: str
    stderr: str
    return_code: int


def run_bandit(root: Path, timeout_s: float = 30.0) -> BanditScan:
    workspace = root.resolve()
    with tempfile.TemporaryDirectory(prefix="aegis-bandit-") as tool_home:
        completed = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", ".", "-f", "json"],
            cwd=workspace,
            env={
                "PATH": str(Path(sys.executable).parent),
                "PYTHONHASHSEED": "0",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
                "HOME": tool_home,
                "USERPROFILE": tool_home,
                "LOCALAPPDATA": tool_home,
                "TEMP": tool_home,
                "TMP": tool_home,
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BanditOutputError("Bandit did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise BanditOutputError("Bandit JSON root must be an object")

    results = payload.get("results")
    errors = payload.get("errors")
    if not isinstance(results, list) or not all(
        isinstance(result, dict) for result in results
    ):
        raise BanditOutputError("Bandit JSON has an invalid results collection")
    if not isinstance(errors, list):
        raise BanditOutputError("Bandit JSON has an invalid errors collection")
    if errors:
        raise BanditOutputError("Bandit reported one or more files it could not scan")
    if completed.returncode not in {0, 1}:
        raise BanditOutputError(
            f"Bandit runner failed with exit code {completed.returncode}"
        )

    return BanditScan(
        results=tuple(results),
        errors=tuple(errors),
        stdout=completed.stdout,
        stderr=completed.stderr,
        return_code=completed.returncode,
    )
