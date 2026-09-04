from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import StreamingResponse

from backend.api.errors import ApiError
from backend.api.runtime import ApiRuntime
from backend.api.schemas import (
    AttemptDetail,
    AttemptSummary,
    EventResponse,
    FindingResponse,
    JobCreate,
    JobRef,
    JobResponse,
)
from backend.core.models import Attempt, Event, Finding, Job
from backend.core.states import JobState, TERMINAL


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_runtime(request: Request) -> ApiRuntime:
    return request.app.state.runtime


@router.post("", response_model=JobRef, status_code=status.HTTP_202_ACCEPTED)
async def create_job(payload: JobCreate, request: Request) -> JobRef:
    runtime = get_runtime(request)
    job = _new_job(
        repository_url=payload.repository_url,
        base_sha=payload.commit_sha,
        mode=payload.mode,
        scenario=payload.scenario,
        max_attempts=runtime.max_attempts,
    )
    runtime.jobs.create(job)
    runtime.launch(job.id)
    return _job_ref(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs(request: Request) -> list[JobResponse]:
    runtime = get_runtime(request)
    return [_job_response(runtime, job) for job in runtime.jobs.list_all()]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, request: Request) -> JobResponse:
    runtime = get_runtime(request)
    return _job_response(runtime, _require_job(runtime, job_id))


@router.get("/{job_id}/events", response_model=list[EventResponse])
async def get_events(
    job_id: str,
    request: Request,
    after: int = 0,
) -> list[EventResponse]:
    runtime = get_runtime(request)
    _require_job(runtime, job_id)
    if after < 0:
        raise ApiError(422, "validation", "invalid_event_cursor", "after must be non-negative")
    return [
        _event_response(event)
        for event in runtime.events.list_for_job(job_id, since_seq=after)
    ]


@router.get("/{job_id}/stream")
async def stream_events(
    job_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    after: int = 0,
) -> StreamingResponse:
    runtime = get_runtime(request)
    _require_job(runtime, job_id)
    if after < 0:
        raise ApiError(
            422,
            "validation",
            "invalid_event_cursor",
            "after must be non-negative",
        )
    return event_stream_response(
        runtime,
        job_id,
        request,
        max(after, _event_cursor(last_event_id)),
    )


@router.get("/{job_id}/attempts", response_model=list[AttemptSummary])
async def list_attempts(job_id: str, request: Request) -> list[AttemptSummary]:
    runtime = get_runtime(request)
    _require_job(runtime, job_id)
    return [
        _attempt_summary(attempt)
        for attempt in runtime.attempts.list_for_job(job_id)
    ]


@router.get("/{job_id}/attempts/{attempt_number}", response_model=AttemptDetail)
async def get_attempt(
    job_id: str,
    attempt_number: int,
    request: Request,
) -> AttemptDetail:
    runtime = get_runtime(request)
    _require_job(runtime, job_id)
    attempt = runtime.attempts.get(job_id, attempt_number)
    if attempt is None:
        raise ApiError(
            404,
            "validation",
            "attempt_not_found",
            f"attempt {attempt_number} was not found",
            job_id=job_id,
        )
    return _attempt_detail(runtime, attempt)


def event_stream_response(
    runtime: ApiRuntime,
    job_id: str,
    request: Request,
    after_seq: int = 0,
) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(runtime, job_id, request, after_seq),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_stream(
    runtime: ApiRuntime,
    job_id: str,
    request: Request,
    after_seq: int,
) -> AsyncIterator[str]:
    terminal_without_replay = (
        JobState(_require_job(runtime, job_id).state) in TERMINAL
        and not runtime.events.list_for_job(job_id, since_seq=after_seq)
    )
    if terminal_without_replay:
        return
    subscription = await runtime.event_bus.subscribe(job_id, after_seq=after_seq)
    async with subscription:
        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(anext(subscription), timeout=15)
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            yield _format_sse(event)
            if _terminal_event(event):
                return


def _format_sse(event: Event) -> str:
    payload = _event_response(event).model_dump_json()
    return f"id: {event.seq}\nevent: {event.type}\ndata: {payload}\n\n"


def _terminal_event(event: Event) -> bool:
    if event.type != "state_changed":
        return False
    data = _json_object(event.data_json)
    state = data.get("state")
    return isinstance(state, str) and JobState(state) in TERMINAL


def _event_cursor(value: str | None) -> int:
    if value is None:
        return 0
    try:
        cursor = int(value)
    except ValueError as exc:
        raise ApiError(
            400,
            "validation",
            "invalid_last_event_id",
            "Last-Event-ID must be a non-negative integer",
        ) from exc
    if cursor < 0:
        raise ApiError(
            400,
            "validation",
            "invalid_last_event_id",
            "Last-Event-ID must be a non-negative integer",
        )
    return cursor


def _require_job(runtime: ApiRuntime, job_id: str) -> Job:
    job = runtime.jobs.get(job_id)
    if job is None:
        raise ApiError(
            404,
            "validation",
            "job_not_found",
            "job was not found",
            job_id=job_id,
        )
    return job


def _new_job(
    *,
    repository_url: str,
    base_sha: str,
    mode: str,
    scenario: str | None,
    max_attempts: int,
) -> Job:
    repository = Path(repository_url.rstrip("/\\")).name.removesuffix(".git")
    return Job(
        id=f"job_{uuid4().hex[:12]}",
        repository=repository or repository_url,
        repository_url=repository_url,
        base_sha=base_sha,
        mode=mode,
        scenario=scenario,
        max_attempts=max_attempts,
        sandbox_tier="docker",
    )


def _job_ref(job: Job) -> JobRef:
    return JobRef(
        job_id=job.id,
        status=job.state,
        stream_url=f"/api/jobs/{job.id}/stream",
    )


def _job_response(runtime: ApiRuntime, job: Job) -> JobResponse:
    findings = runtime.findings.list_for_job(job.id)
    finding = _finding_response(findings[0]) if findings else None
    return JobResponse(**asdict(job), finding=finding)


def _finding_response(finding: Finding) -> FindingResponse:
    return FindingResponse(
        id=finding.id,
        cwe=finding.cwe,
        category=finding.category,
        severity=finding.severity,
        file=finding.file_path,
        line=finding.line_start,
        symbol=finding.symbol,
        scanner=finding.scanner,
        message=finding.message,
    )


def _event_response(event: Event) -> EventResponse:
    if event.seq is None:
        raise ValueError("only persisted events may cross the API boundary")
    return EventResponse(
        seq=event.seq,
        job_id=event.job_id,
        ts=event.ts,
        type=event.type,
        severity=event.severity,
        attempt=event.attempt,
        title=event.title,
        message=event.message,
        data=_json_object(event.data_json) if event.data_json else None,
    )


def _attempt_summary(attempt: Attempt) -> AttemptSummary:
    return AttemptSummary(
        attempt=attempt.attempt_number,
        model=attempt.model,
        decision=attempt.decision,
        summary=attempt.summary,
        files_changed=attempt.files_changed,
        lines_added=attempt.lines_added,
        lines_removed=attempt.lines_removed,
        failure_gate=attempt.failure_gate,
        failure_reason=attempt.failure_reason,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        duration_ms=attempt.duration_ms,
    )


def _attempt_detail(runtime: ApiRuntime, attempt: Attempt) -> AttemptDetail:
    explanation = _json_object(attempt.explain_json)
    rationale = explanation.pop("rationale", None)
    gates = {
        "policy": _json_object(attempt.policy_json),
        "security": _json_object(attempt.security_json),
        "regression": _json_object(attempt.regression_json),
        "post_scan": _json_object(attempt.post_scan_json),
        "integrity": _json_object(attempt.integrity_json),
        "explain": explanation,
    }
    return AttemptDetail(
        **_attempt_summary(attempt).model_dump(),
        diff=_artifact_content(runtime, attempt.diff_ref),
        gates=gates,
        rationale=rationale if isinstance(rationale, dict) else None,
        raw={
            "pytest": _artifact_content(runtime, attempt.pytest_ref),
            "bandit": _artifact_content(runtime, attempt.bandit_ref),
            "harness": _artifact_content(runtime, attempt.harness_ref),
        },
        tree_hash_pre=attempt.tree_hash_pre,
        tree_hash_post=attempt.tree_hash_post,
    )


def _artifact_content(runtime: ApiRuntime, reference: str | None) -> str | None:
    if reference is None:
        return None
    artifact = runtime.artifacts.get(reference)
    return artifact.content if artifact is not None else None


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}
