from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
from shutil import which
import subprocess
import sys
import tempfile
from time import perf_counter
from typing import Awaitable, Literal
from urllib.parse import quote

if __package__ in {None, ""}:
    # Direct script execution otherwise exposes only scripts/ on sys.path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from pydantic import ValidationError

from backend.agent.feather_client import FeatherPatchModel
from backend.core.config import (
    FeatherSettings,
    GitHubSettings,
    ModelChainError,
    RuntimeSettings,
    load_model_chain,
)
from backend.core.replay import ReplayArchive, ReplayError
from backend.core.workspace import read_text
from backend.storage.database import Database
from scripts.verify_feather import SMOKE_CONTEXT, SMOKE_FINDING


PROJECT_ROOT = Path(__file__).resolve().parents[1]
Level = Literal["ok", "warn", "fail"]

# A preflight is run minutes before a demo, so every probe is bounded and the
# total is bounded too. An unbounded readiness check is worse than no check:
# it fails by hanging, at exactly the moment nobody can afford to wait.
REMOTE_PROBE_TIMEOUT = 25.0
DOCKER_COMMAND_TIMEOUT = 10.0
GIT_PROBE_TIMEOUT = 5.0
BENCHMARK_CASE_COUNT = 10

# Derived, not guessed: the sum of every probe's ceiling plus slack. Hardcoding
# a number here lets a raised probe timeout silently exceed it, which would make
# the budget check warn on a run that was in fact correctly bounded.
PREFLIGHT_BUDGET_SECONDS = (
    DOCKER_COMMAND_TIMEOUT * 2          # docker version + image inspect
    + GIT_PROBE_TIMEOUT * BENCHMARK_CASE_COUNT
    + REMOTE_PROBE_TIMEOUT              # feather and github run concurrently
    + 10.0                              # sqlite, replay scan, process startup
)


@dataclass(frozen=True, slots=True)
class CheckResult:
    level: Level
    name: str
    detail: str = ""

    def render(self) -> str:
        suffix = f" -> {self.detail}" if self.detail else ""
        return f"[{self.level}]".ljust(7) + f"{self.name}{suffix}"


def check_python() -> CheckResult:
    version = sys.version_info
    supported = version >= (3, 11) and version < (3, 13)
    return CheckResult(
        "ok" if supported else "fail",
        f"python {version.major}.{version.minor}.{version.micro} orchestrator interpreter",
        "supported" if supported else "requires Python 3.11 or 3.12",
    )


def check_docker(image: str) -> tuple[CheckResult, CheckResult]:
    executable = which("docker")
    if executable is None:
        unavailable = CheckResult("fail", "docker daemon reachable", "docker executable not found")
        return unavailable, CheckResult("fail", f"image {image} present", "docker unavailable")

    version = _run_command(
        executable, "version", "--format", "{{.Server.Version}}", timeout=DOCKER_COMMAND_TIMEOUT
    )
    daemon_ok = version.returncode == 0 and bool(version.stdout.strip())
    daemon = CheckResult(
        "ok" if daemon_ok else "fail",
        "docker daemon reachable",
        f"sandbox tier: DOCKER ({version.stdout.strip()})" if daemon_ok else _command_error(version),
    )
    if not daemon_ok:
        return daemon, CheckResult("fail", f"image {image} present", "docker daemon unavailable")

    inspected = _run_command(
        executable, "image", "inspect", image, timeout=DOCKER_COMMAND_TIMEOUT
    )
    return daemon, CheckResult(
        "ok" if inspected.returncode == 0 else "fail",
        f"image {image} present",
        "ready" if inspected.returncode == 0 else "run SandboxRunner.ensure_image()",
    )


def check_model_chain() -> CheckResult:
    """Report the configured provider chain without contacting anyone.

    A single configured provider is a demo with no redundancy, which is a
    warning rather than a failure: it still works, right up until a quota runs
    out mid-run.
    """
    try:
        chain = load_model_chain()
    except ModelChainError as exc:
        return CheckResult("fail", "model chain configured", str(exc)[:160])
    described = " -> ".join(f"{slot.label}:{slot.model}" for slot in chain)
    return CheckResult(
        "ok" if len(chain) > 1 else "warn",
        f"model chain: {len(chain)} provider(s)",
        described if len(chain) > 1 else f"{described} (no fallback configured)",
    )


async def check_feather() -> CheckResult:
    try:
        settings = FeatherSettings().model_copy(
            update={"timeout_seconds": 20.0, "transport_retries": 0}
        )
    except ValidationError:
        return CheckResult("fail", "FEATHER_API_KEY set", "configuration missing or invalid")

    started = perf_counter()
    try:
        await FeatherPatchModel(settings).generate_patch(
            SMOKE_FINDING,
            context=SMOKE_CONTEXT,
            policy_summary=(
                "Change at most three existing Python files. Do not modify tests or "
                "dependencies. Return complete file contents."
            ),
        )
    except Exception as exc:
        return CheckResult(
            "fail",
            "FEATHER_API_KEY schema-conformant round-trip",
            _safe_error(exc),
        )
    elapsed_ms = round((perf_counter() - started) * 1000)
    return CheckResult(
        "ok",
        "FEATHER_API_KEY schema-conformant round-trip",
        f"{elapsed_ms}ms using {settings.model}",
    )


async def check_github() -> CheckResult:
    try:
        settings = GitHubSettings()
    except ValidationError:
        return CheckResult("fail", "GitHub delivery credentials", "configuration is invalid")
    if settings.token is None or not settings.owner or not settings.repo:
        return CheckResult(
            "fail",
            "GitHub delivery credentials",
            "GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO are required",
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.token.get_secret_value()}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    path = f"/repos/{quote(settings.owner, safe='')}/{quote(settings.repo, safe='')}"
    try:
        async with httpx.AsyncClient(
            base_url=settings.api_url.rstrip("/"),
            headers=headers,
            timeout=min(settings.timeout_seconds, 20.0),
        ) as client:
            response = await client.get(path)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return CheckResult("fail", "GitHub delivery credentials", _safe_error(exc))

    permissions = payload.get("permissions") if isinstance(payload, dict) else None
    can_push = isinstance(permissions, dict) and permissions.get("push") is True
    return CheckResult(
        "ok" if can_push else "fail",
        "GitHub delivery credentials",
        (
            f"{settings.owner}/{settings.repo} reachable with write access"
            if can_push
            else f"{settings.owner}/{settings.repo} does not report push permission"
        ),
    )


def check_benchmarks(project_root: Path) -> tuple[CheckResult, CheckResult]:
    manifest_path = project_root / "benchmarks" / "MANIFEST.json"
    try:
        manifest = json.loads(read_text(manifest_path))
        cases = manifest["cases"]
        case_ids = [str(item["id"]) for item in cases]
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError) as exc:
        failure = CheckResult("fail", "10 benchmark fixtures present", _safe_error(exc))
        return failure, CheckResult("fail", "core.autocrlf == false", "manifest unavailable")

    missing = [
        case_id
        for case_id in case_ids
        if not (project_root / "benchmarks" / case_id / ".git").is_dir()
    ]
    fixtures_ok = len(case_ids) == 10 and not missing
    fixture_detail = (
        "all git-initialised"
        if fixtures_ok
        else f"found {len(case_ids)} cases; missing git metadata: {', '.join(missing) or 'none'}"
    )

    git = which("git")
    wrong_autocrlf: list[str] = []
    if git is None:
        wrong_autocrlf = case_ids
    else:
        for case_id in case_ids:
            fixture = project_root / "benchmarks" / case_id
            if not fixture.is_dir():
                continue
            result = _run_command(
                git,
                "-C",
                str(fixture),
                "config",
                "--get",
                "core.autocrlf",
                timeout=GIT_PROBE_TIMEOUT,
            )
            if result.returncode != 0 or result.stdout.strip().lower() != "false":
                wrong_autocrlf.append(case_id)

    return (
        CheckResult("ok" if fixtures_ok else "fail", "10 benchmark fixtures present", fixture_detail),
        CheckResult(
            "ok" if not wrong_autocrlf else "fail",
            "core.autocrlf == false in all benchmark workspaces",
            "confirmed" if not wrong_autocrlf else f"incorrect: {', '.join(wrong_autocrlf)}",
        ),
    )


def check_sqlite(db_path: Path) -> CheckResult:
    try:
        database = Database(db_path)
        connection = database.init_db()
        try:
            mode = database.check_wal(connection)
        finally:
            connection.close()
    except Exception as exc:
        return CheckResult("fail", "sqlite writable, WAL enabled", _safe_error(exc))
    return CheckResult(
        "ok" if mode == "wal" else "fail",
        "sqlite writable, WAL enabled",
        f"journal_mode={mode}",
    )


def check_replays(replay_dir: Path) -> CheckResult:
    try:
        count = len(ReplayArchive(replay_dir).list())
    except ReplayError as exc:
        return CheckResult("fail", "replay recordings", _safe_error(exc))
    level: Level = "ok" if count >= 3 else "warn"
    detail = "offline fallback ready" if count >= 3 else "recommend 3"
    return CheckResult(level, f"replay/ has {count} recorded runs", detail)


async def run_checks(project_root: Path, *, offline: bool = False) -> list[CheckResult]:
    runtime = RuntimeSettings()
    image = os.getenv("AEGIS_SANDBOX_IMAGE", "aegis-sandbox:py311")
    docker_daemon, docker_image = check_docker(image)
    if offline:
        feather = _skipped("FEATHER_API_KEY schema-conformant round-trip")
        github = _skipped("GitHub delivery credentials")
    else:
        feather, github = await asyncio.gather(
            _bounded_remote(check_feather(), "FEATHER_API_KEY schema-conformant round-trip"),
            _bounded_remote(check_github(), "GitHub delivery credentials"),
        )
    fixtures, autocrlf = check_benchmarks(project_root)
    db_path = runtime.db_path if runtime.db_path.is_absolute() else project_root / runtime.db_path
    replay_dir = runtime.replay_dir if runtime.replay_dir.is_absolute() else project_root / runtime.replay_dir
    return [
        check_python(),
        docker_daemon,
        docker_image,
        check_model_chain(),
        feather,
        github,
        autocrlf,
        check_sqlite(db_path),
        fixtures,
        check_replays(replay_dir),
    ]


async def _bounded_remote(
    check: Awaitable[CheckResult],
    name: str,
) -> CheckResult:
    # A provider that keeps trickling bytes resets httpx's read timeout
    # indefinitely, so the per-operation timeout alone does not bound the call.
    # This is the hard wall-clock ceiling.
    try:
        return await asyncio.wait_for(check, timeout=REMOTE_PROBE_TIMEOUT)
    except TimeoutError:
        return CheckResult("fail", name, f"hard timeout after {REMOTE_PROBE_TIMEOUT:g}s")


def _skipped(name: str) -> CheckResult:
    return CheckResult("warn", name, "skipped (--offline)")


def check_budget(elapsed_seconds: float) -> CheckResult:
    within = elapsed_seconds <= PREFLIGHT_BUDGET_SECONDS
    return CheckResult(
        "ok" if within else "warn",
        "preflight completed within budget",
        f"{elapsed_seconds:.1f}s of {PREFLIGHT_BUDGET_SECONDS:g}s",
    )


def _run_command(
    executable: str,
    *arguments: str,
    timeout: float = DOCKER_COMMAND_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="aegis-preflight-") as temporary:
        environment = {
            "PATH": str(Path(executable).parent),
            "HOME": temporary,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
        }
        for name in ("SYSTEMROOT", "WINDIR", "DOCKER_HOST", "DOCKER_CONTEXT"):
            value = os.environ.get(name)
            if value:
                environment[name] = value
        try:
            return subprocess.run(
                [executable, *arguments],
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                [executable, *arguments],
                returncode=124,
                stdout="",
                stderr=f"command timed out after {timeout:g}s",
            )


def _command_error(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr.strip() or result.stdout.strip() or "command failed")[:240]


def _safe_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}"
    return error.__class__.__name__


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify AegisAgent demo prerequisites")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the Feather and GitHub probes; check only what runs locally",
    )
    arguments = parser.parse_args()

    started = perf_counter()
    results = asyncio.run(run_checks(PROJECT_ROOT, offline=arguments.offline))
    results.append(check_budget(perf_counter() - started))

    for result in results:
        print(result.render())
    failures = sum(item.level == "fail" for item in results)
    warnings = sum(item.level == "warn" for item in results)
    print(
        f"\npreflight: {len(results) - failures - warnings} ok, "
        f"{warnings} warnings, {failures} failures"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
