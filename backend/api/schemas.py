from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_url: str = Field(min_length=1)
    commit_sha: str = Field(default="HEAD", min_length=1)
    mode: Literal["demo", "live"] = "live"
    scenario: str | None = None


class JobRef(BaseModel):
    job_id: str
    status: str
    stream_url: str


class FindingResponse(BaseModel):
    id: str
    cwe: str
    category: str
    severity: str
    file: str
    line: int
    symbol: str
    scanner: str
    message: str


class JobResponse(BaseModel):
    id: str
    repository: str
    repository_url: str
    base_sha: str
    mode: str
    scenario: str | None
    state: str
    current_attempt: int
    max_attempts: int
    sandbox_tier: str | None
    final_decision: str | None
    final_reason: str | None
    branch_name: str | None
    pr_url: str | None
    pr_number: int | None
    repository_changed: bool
    finding: FindingResponse | None = None
    created_at: str
    updated_at: str
    completed_at: str | None


class EventResponse(BaseModel):
    seq: int
    job_id: str
    ts: str
    type: str
    severity: str
    attempt: int | None
    title: str
    message: str | None
    data: dict[str, Any] | None


class AttemptSummary(BaseModel):
    attempt: int
    model: str | None
    decision: str
    summary: str | None
    files_changed: int | None
    lines_added: int | None
    lines_removed: int | None
    failure_gate: str | None
    failure_reason: str | None
    started_at: str | None
    completed_at: str | None
    duration_ms: int | None


class AttemptDetail(AttemptSummary):
    diff: str | None
    gates: dict[str, Any]
    rationale: dict[str, Any] | None
    raw: dict[str, Any]
    tree_hash_pre: str | None
    tree_hash_post: str | None


class BenchmarkScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    difficulty: Literal["easy", "medium", "hard", "expert"]
    language: str
    vulnerability_types: list[str]
    expected_decision: str
    expected_attempts: int | None


class BenchmarkRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)


class BenchmarkRunResponse(BaseModel):
    id: int
    case_id: str
    job_id: str
    expected_decision: str
    actual_decision: str | None
    attempts_used: int | None
    duration_ms: int | None
    correct: bool | None
    false_verification: bool
    status: Literal["running", "completed"]
    run_at: str


class BenchmarkMetricsResponse(BaseModel):
    total_runs: int
    completed_runs: int
    correct_runs: int
    false_verifications: int


ErrorKind: TypeAlias = Literal[
    "technical",
    "policy",
    "escalation",
    "reproduction",
    "validation",
]


class ErrorBody(BaseModel):
    kind: ErrorKind
    code: str
    message: str
    job_id: str | None = None
    retryable: bool = False


class ErrorEnvelope(BaseModel):
    error: ErrorBody
