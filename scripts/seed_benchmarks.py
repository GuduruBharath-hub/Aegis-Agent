from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.workspace import read_text


def seed_benchmark_repositories(project_root: Path = PROJECT_ROOT) -> tuple[str, ...]:
    benchmarks = project_root / "benchmarks"
    manifest = json.loads(read_text(benchmarks / "MANIFEST.json"))
    case_ids = tuple(str(case["id"]) for case in manifest["cases"])
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable not found")
    seeded: list[str] = []
    for case_id in case_ids:
        fixture = benchmarks / case_id
        if not fixture.is_dir():
            raise RuntimeError(f"benchmark fixture is missing: {case_id}")
        if (fixture / ".git").is_dir():
            continue
        _git(git, fixture, "init")
        _git(git, fixture, "config", "core.autocrlf", "false")
        _git(git, fixture, "config", "user.name", "AegisAgent Fixtures")
        _git(git, fixture, "config", "user.email", "fixtures@aegis.invalid")
        _git(git, fixture, "add", ".")
        _git(git, fixture, "commit", "-m", f"fixture: seed {case_id}")
        seeded.append(case_id)
    return tuple(seeded)


def _git(git: str, fixture: Path, *args: str) -> None:
    completed = subprocess.run(
        [git, *args],
        cwd=fixture,
        env={
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "NUL" if shutil.which("cmd") else "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed for {fixture.name}: {detail}")


def main() -> int:
    seeded = seed_benchmark_repositories()
    print(f"seeded {len(seeded)} benchmark repositories")
    for case_id in seeded:
        print(f"- {case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
