from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
from time import perf_counter

import pytest
from pydantic import SecretStr

from backend.core.config import ModelSlot
from backend.core.replay import ReplayArchive, ReplaySummary
from scripts import verify_env


def test_local_preflight_checks_repository_and_sqlite(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    fixtures, autocrlf = verify_env.check_benchmarks(project_root)
    sqlite = verify_env.check_sqlite(tmp_path / "preflight.db")

    assert verify_env.check_python().level == "ok"
    assert fixtures.level == "ok"
    assert autocrlf.level == "ok"
    assert sqlite.level == "ok"
    assert "journal_mode=wal" in sqlite.detail


def test_replay_preflight_warns_until_three_valid_recordings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ReplayArchive, "list", lambda self: [])
    warning = verify_env.check_replays(tmp_path)

    recordings = [
        ReplaySummary(
            id=f"run-{index}",
            source_job_id=f"job-{index}",
            scenario="sql_retry",
            final_decision="verified",
            attempts=2,
            event_count=10,
            recorded_at="2026-09-05T00:00:00+00:00",
        )
        for index in range(3)
    ]
    monkeypatch.setattr(ReplayArchive, "list", lambda self: recordings)
    ready = verify_env.check_replays(tmp_path)

    assert warning.level == "warn"
    assert ready.level == "ok"


def test_preflight_subprocess_environment_does_not_forward_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "must-not-enter-a-subprocess"
    monkeypatch.setenv("FEATHER_API_KEY", sentinel)
    monkeypatch.setenv("GITHUB_TOKEN", sentinel)
    captured: dict[str, str] = {}

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del command
        captured.update(kwargs["env"])  # type: ignore[arg-type]
        return subprocess.CompletedProcess([], 0, stdout="false\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    verify_env._run_command("C:/tools/git.exe", "config", "core.autocrlf")

    assert "FEATHER_API_KEY" not in captured
    assert "GITHUB_TOKEN" not in captured
    assert sentinel not in captured.values()


def test_check_result_render_is_stable_for_demo_output() -> None:
    result = verify_env.CheckResult("ok", "docker daemon reachable", "sandbox tier: DOCKER")

    assert result.render() == "[ok]   docker daemon reachable -> sandbox tier: DOCKER"


def test_feather_probe_uses_configured_primary_with_bounded_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = ModelSlot(
        label="primary",
        api_key=SecretStr("secret"),
        base_url="https://provider.example/v1",
        model="configured-primary",
        max_tokens=8_000,
        temperature=0.0,
        timeout_seconds=60.0,
        concurrency=1,
        transport_retries=2,
    )
    captured: dict[str, object] = {}

    class FakePatchModel:
        def __init__(self, settings: ModelSlot) -> None:
            captured["settings"] = settings

        async def generate_patch(self, *args: object, **kwargs: object) -> object:
            del args, kwargs
            return object()

    monkeypatch.setattr(verify_env, "load_model_chain", lambda: (primary,))
    monkeypatch.setattr(verify_env, "FeatherPatchModel", FakePatchModel)

    result = asyncio.run(verify_env.check_feather())
    used = captured["settings"]

    assert isinstance(used, ModelSlot)
    assert used.model == "configured-primary"
    assert used.timeout_seconds == verify_env.MODEL_OPERATION_TIMEOUT
    assert used.transport_retries == 0
    assert result.level == "ok"
    assert "configured-primary" in result.detail


def test_remote_probe_is_bounded_by_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """A provider that never stops sending must not stall the preflight.

    httpx's read timeout is per-operation and resets on every byte, so only a
    hard ceiling around the whole call bounds it.
    """
    monkeypatch.setattr(verify_env, "REMOTE_PROBE_TIMEOUT", 0.05)

    async def never_returns() -> verify_env.CheckResult:
        await asyncio.sleep(30)
        raise AssertionError("probe should have been cancelled")

    started = perf_counter()
    result = asyncio.run(verify_env._bounded_remote(never_returns(), "feather round-trip"))

    assert result.level == "fail"
    assert "hard timeout" in result.detail
    assert perf_counter() - started < 5.0


def test_offline_mode_skips_remote_probes_without_calling_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def explode() -> verify_env.CheckResult:  # pragma: no cover - must not run
        raise AssertionError("offline preflight must not contact a provider")

    monkeypatch.setattr(verify_env, "check_feather", explode)
    monkeypatch.setattr(verify_env, "check_github", explode)

    results = asyncio.run(
        verify_env.run_checks(Path(__file__).resolve().parents[1], offline=True)
    )
    skipped = [item for item in results if item.detail == "skipped (--offline)"]

    assert len(skipped) == 2
    assert all(item.level == "warn" for item in skipped)


def test_budget_check_warns_when_preflight_overruns() -> None:
    within = verify_env.check_budget(1.5)
    overrun = verify_env.check_budget(verify_env.PREFLIGHT_BUDGET_SECONDS + 1)

    assert within.level == "ok"
    assert overrun.level == "warn"


def test_local_probes_use_short_timeouts() -> None:
    """Local git and docker reads are fast; a 20s ceiling on each would let the
    ten autocrlf probes alone blow the whole preflight budget."""
    assert verify_env.GIT_PROBE_TIMEOUT <= 5.0
    assert verify_env.DOCKER_COMMAND_TIMEOUT <= 10.0
    ceiling = (
        verify_env.DOCKER_COMMAND_TIMEOUT * 2
        + verify_env.GIT_PROBE_TIMEOUT * verify_env.BENCHMARK_CASE_COUNT
        + verify_env.REMOTE_PROBE_TIMEOUT
    )
    assert ceiling <= verify_env.PREFLIGHT_BUDGET_SECONDS
