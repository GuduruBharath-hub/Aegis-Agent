from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, Request, status

from backend.api.errors import ApiError
from backend.api.routes_jobs import _job_ref, get_runtime
from backend.api.schemas import JobRef, ReplayRecordCreate, ReplaySummaryResponse
from backend.core.replay import ReplayError, record_job, restore_job


router = APIRouter(prefix="/api/replays", tags=["replays"])


@router.get("", response_model=list[ReplaySummaryResponse])
async def list_replays(request: Request) -> list[ReplaySummaryResponse]:
    runtime = get_runtime(request)
    try:
        return [
            ReplaySummaryResponse(**asdict(summary))
            for summary in runtime.replay_archive.list()
        ]
    except ReplayError as exc:
        raise _replay_error(exc) from exc


@router.post(
    "/record",
    response_model=ReplaySummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recording(
    payload: ReplayRecordCreate,
    request: Request,
) -> ReplaySummaryResponse:
    runtime = get_runtime(request)
    try:
        summary = record_job(
            payload.recording_id,
            payload.job_id,
            archive=runtime.replay_archive,
            jobs=runtime.jobs,
            findings=runtime.findings,
            attempts=runtime.attempts,
            events=runtime.events,
            artifacts=runtime.artifacts,
        )
    except ReplayError as exc:
        raise _replay_error(exc) from exc
    return ReplaySummaryResponse(**asdict(summary))


@router.post(
    "/{recording_id}",
    response_model=JobRef,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_replay(recording_id: str, request: Request) -> JobRef:
    runtime = get_runtime(request)
    try:
        recording = runtime.replay_archive.load(recording_id)
        job = restore_job(
            recording,
            f"job_replay_{uuid4().hex[:12]}",
            jobs=runtime.jobs,
            findings=runtime.findings,
            attempts=runtime.attempts,
            events=runtime.events,
            artifacts=runtime.artifacts,
        )
    except ReplayError as exc:
        raise _replay_error(exc) from exc
    return _job_ref(job)


def _replay_error(error: ReplayError) -> ApiError:
    message = str(error)
    code = "replay_not_found" if "not found" in message else "invalid_replay"
    status_code = 404 if code == "replay_not_found" else 422
    return ApiError(status_code, "validation", code, message)
