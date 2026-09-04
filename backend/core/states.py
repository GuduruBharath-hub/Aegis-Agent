from __future__ import annotations

from enum import Enum

from backend.core.models import Job


class JobState(str, Enum):
    RECEIVED = "received"
    SCANNING = "scanning"
    FINDING_IDENTIFIED = "finding_identified"
    REPRODUCING = "reproducing"
    REPRODUCED = "reproduced"
    CONTEXT_BUILDING = "context_building"
    GENERATING_PATCH = "generating_patch"
    VALIDATING_PATCH = "validating_patch"
    SANDBOXING = "sandboxing"
    VERIFYING_SECURITY = "verifying_security"
    VERIFYING_REGRESSION = "verifying_regression"
    POST_SCANNING = "post_scanning"
    INTEGRITY_CHECK = "integrity_check"
    RETRYING = "retrying"
    VERIFIED = "verified"
    CREATING_PR = "creating_pr"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    POLICY_REJECTED = "policy_rejected"
    FAILED = "failed"


TERMINAL: frozenset[JobState] = frozenset(
    {
        JobState.COMPLETED,
        JobState.ESCALATED,
        JobState.POLICY_REJECTED,
        JobState.FAILED,
    }
)

LEGAL: dict[JobState, frozenset[JobState]] = {
    JobState.RECEIVED: frozenset({JobState.SCANNING, JobState.FAILED}),
    JobState.SCANNING: frozenset(
        {JobState.FINDING_IDENTIFIED, JobState.ESCALATED, JobState.FAILED}
    ),
    JobState.FINDING_IDENTIFIED: frozenset(
        {JobState.REPRODUCING, JobState.ESCALATED}
    ),
    JobState.REPRODUCING: frozenset(
        {JobState.REPRODUCED, JobState.ESCALATED, JobState.FAILED}
    ),
    JobState.REPRODUCED: frozenset({JobState.CONTEXT_BUILDING}),
    JobState.CONTEXT_BUILDING: frozenset(
        {JobState.GENERATING_PATCH, JobState.FAILED}
    ),
    JobState.GENERATING_PATCH: frozenset(
        {JobState.VALIDATING_PATCH, JobState.FAILED}
    ),
    JobState.VALIDATING_PATCH: frozenset(
        {JobState.SANDBOXING, JobState.RETRYING, JobState.POLICY_REJECTED}
    ),
    JobState.SANDBOXING: frozenset(
        {JobState.VERIFYING_SECURITY, JobState.RETRYING, JobState.FAILED}
    ),
    JobState.VERIFYING_SECURITY: frozenset(
        {JobState.VERIFYING_REGRESSION, JobState.RETRYING}
    ),
    JobState.VERIFYING_REGRESSION: frozenset(
        {JobState.POST_SCANNING, JobState.RETRYING}
    ),
    JobState.POST_SCANNING: frozenset(
        {JobState.INTEGRITY_CHECK, JobState.RETRYING}
    ),
    JobState.INTEGRITY_CHECK: frozenset(
        {JobState.VERIFIED, JobState.RETRYING, JobState.FAILED}
    ),
    JobState.RETRYING: frozenset(
        {JobState.CONTEXT_BUILDING, JobState.ESCALATED}
    ),
    JobState.VERIFIED: frozenset({JobState.CREATING_PR}),
    JobState.CREATING_PR: frozenset({JobState.COMPLETED, JobState.FAILED}),
}


class IllegalTransitionError(ValueError):
    pass


class FinalDecisionOverwriteError(ValueError):
    pass


class TerminalJobUpdateError(ValueError):
    pass


def validate_transition(current: JobState | str, target: JobState | str) -> None:
    try:
        current_state = JobState(current)
        target_state = JobState(target)
    except ValueError as exc:
        raise IllegalTransitionError(f"unknown job state: {exc}") from exc

    if target_state not in LEGAL.get(current_state, frozenset()):
        raise IllegalTransitionError(
            f"illegal job transition: {current_state.value} -> {target_state.value}"
        )


def validate_job_update(current: Job, proposed: Job) -> None:
    if current.id != proposed.id:
        raise ValueError("a persisted job cannot change its id")

    current_state = _coerce_state(current.state)
    proposed_state = _coerce_state(proposed.state)

    if (
        current.final_decision is not None
        and proposed.final_decision != current.final_decision
    ):
        raise FinalDecisionOverwriteError(
            f"final decision for job {current.id} cannot be overwritten"
        )

    if current_state in TERMINAL and proposed != current:
        raise TerminalJobUpdateError(
            f"terminal job {current.id} cannot be modified"
        )

    if current_state != proposed_state:
        validate_transition(current_state, proposed_state)


def _coerce_state(value: str) -> JobState:
    try:
        return JobState(value)
    except ValueError as exc:
        raise IllegalTransitionError(f"unknown job state: {value}") from exc
