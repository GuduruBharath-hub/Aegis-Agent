from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, status

from backend.api.errors import ApiError
from backend.api.routes_demo import _create_demo_job
from backend.api.routes_jobs import get_runtime
from backend.api.schemas import (
    BenchmarkMetricsResponse,
    BenchmarkRunCreate,
    BenchmarkRunResponse,
    BenchmarkScenarioResponse,
)
from backend.core.models import BenchmarkRun
from backend.core.workspace import read_text


router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


@router.get("/scenarios", response_model=list[BenchmarkScenarioResponse])
async def list_scenarios(request: Request) -> list[BenchmarkScenarioResponse]:
    return [_scenario_response(item) for item in _manifest(request).values()]


@router.post(
    "/run",
    response_model=BenchmarkRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_benchmark(
    payload: BenchmarkRunCreate,
    request: Request,
) -> BenchmarkRunResponse:
    runtime = get_runtime(request)
    scenario = _manifest(request).get(payload.scenario_id)
    if scenario is None:
        raise ApiError(
            404,
            "validation",
            "unknown_benchmark_scenario",
            f"unknown benchmark scenario: {payload.scenario_id}",
        )
    job = _create_demo_job(runtime, payload.scenario_id)
    runtime.jobs.create(job)
    run = runtime.benchmark_runs.create(
        BenchmarkRun(
            case_id=payload.scenario_id,
            job_id=job.id,
            expected_decision=str(scenario["expected_decision"]),
        )
    )
    if run.id is None:
        raise RuntimeError("persisted benchmark run has no id")
    runtime.launch(job.id, benchmark_run_id=run.id)
    return _run_response(run)


@router.get("/runs", response_model=list[BenchmarkRunResponse])
async def list_runs(request: Request) -> list[BenchmarkRunResponse]:
    runtime = get_runtime(request)
    return [_run_response(run) for run in runtime.benchmark_runs.list_all()]


@router.get("/runs/{run_id}", response_model=BenchmarkRunResponse)
async def get_run(run_id: int, request: Request) -> BenchmarkRunResponse:
    run = get_runtime(request).benchmark_runs.get(run_id)
    if run is None:
        raise ApiError(404, "validation", "benchmark_run_not_found", "run was not found")
    return _run_response(run)


@router.get("/metrics", response_model=BenchmarkMetricsResponse)
async def get_metrics(request: Request) -> BenchmarkMetricsResponse:
    runs = get_runtime(request).benchmark_runs.list_all()
    completed = [run for run in runs if run.actual_decision is not None]
    return BenchmarkMetricsResponse(
        total_runs=len(runs),
        completed_runs=len(completed),
        correct_runs=sum(run.correct is True for run in completed),
        false_verifications=sum(
            run.expected_decision != "verified" and run.actual_decision == "verified"
            for run in completed
        ),
    )


def _manifest(request: Request) -> dict[str, dict[str, Any]]:
    path = Path(get_runtime(request).project_root) / "benchmarks" / "MANIFEST.json"
    try:
        payload = json.loads(read_text(path))
    except (OSError, ValueError) as exc:
        raise ApiError(
            500,
            "technical",
            "benchmark_manifest_invalid",
            "benchmark manifest is unavailable or invalid",
        ) from exc
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        raise ApiError(500, "technical", "benchmark_manifest_invalid", "cases must be a list")
    return {
        str(item["id"]): item
        for item in cases
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _scenario_response(item: dict[str, Any]) -> BenchmarkScenarioResponse:
    return BenchmarkScenarioResponse.model_validate(item)


def _run_response(run: BenchmarkRun) -> BenchmarkRunResponse:
    if run.id is None:
        raise ValueError("only persisted benchmark runs may cross the API boundary")
    return BenchmarkRunResponse(
        id=run.id,
        case_id=run.case_id,
        job_id=run.job_id,
        expected_decision=run.expected_decision,
        actual_decision=run.actual_decision,
        attempts_used=run.attempts_used,
        duration_ms=run.duration_ms,
        correct=run.correct,
        false_verification=(
            run.expected_decision != "verified" and run.actual_decision == "verified"
        ),
        status="running" if run.actual_decision is None else "completed",
        run_at=run.run_at,
    )
