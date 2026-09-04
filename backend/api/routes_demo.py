from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from backend.api.errors import ApiError
from backend.api.routes_jobs import (
    _job_ref,
    _new_job,
    event_stream_response,
    get_runtime,
)
from backend.api.schemas import JobRef
from backend.api.runtime import ApiRuntime
from backend.core.models import Job


router = APIRouter(prefix="/api/demo", tags=["demo"])
SUPPORTED_SCENARIOS = frozenset(
    {
        "sql_basic",
        "sql_retry",
        "cmd_basic",
        "cmd_retry",
        "sql_unsupported",
        "repro_fail",
        "policy_hidden_test",
        "policy_diff_bomb",
        "policy_bad_api",
        "unsolvable",
    }
)


@router.post(
    "/{scenario}",
    response_model=JobRef,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_demo(scenario: str, request: Request) -> JobRef:
    runtime = get_runtime(request)
    job = _create_demo_job(runtime, scenario)
    runtime.jobs.create(job)
    runtime.launch(job.id)
    return _job_ref(job)


@router.get("/{scenario}")
async def stream_demo(scenario: str, request: Request) -> StreamingResponse:
    """CLI shortcut: create a demo and stream its durable event log."""
    runtime = get_runtime(request)
    job = _create_demo_job(runtime, scenario)
    runtime.jobs.create(job)
    runtime.launch(job.id)
    return event_stream_response(runtime, job.id, request)


def _create_demo_job(runtime: ApiRuntime, scenario: str) -> Job:
    if scenario not in SUPPORTED_SCENARIOS:
        raise ApiError(
            404,
            "validation",
            "unknown_demo_scenario",
            f"unsupported demo scenario: {scenario}",
        )
    benchmark = runtime.project_root / "benchmarks" / scenario
    if not benchmark.is_dir():
        raise ApiError(
            404,
            "technical",
            "demo_fixture_missing",
            f"demo fixture is unavailable: {scenario}",
        )
    return _new_job(
        repository_url=str(benchmark),
        base_sha="HEAD",
        mode="demo",
        scenario=scenario,
        max_attempts=runtime.max_attempts,
    )
