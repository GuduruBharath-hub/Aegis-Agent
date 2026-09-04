from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    scanner: str
    rule_id: str
    category: str
    cwe: str
    severity: str
    confidence: str
    file_path: str
    line_start: int
    line_end: int
    symbol: str
    message: str


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    repository: str
    repository_url: str
    base_sha: str
    mode: str
    max_attempts: int
    state: str = "received"
    scenario: str | None = None
    current_attempt: int = 0
    sandbox_tier: str | None = None
    final_decision: str | None = None
    final_reason: str | None = None
    branch_name: str | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    completed_at: str | None = None


@dataclass(frozen=True, slots=True)
class Attempt:
    job_id: str
    attempt_number: int
    decision: str = "in_progress"
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    summary: str | None = None
    files_changed: int | None = None
    lines_added: int | None = None
    lines_removed: int | None = None
    diff_ref: str | None = None
    policy_json: str | None = None
    security_json: str | None = None
    regression_json: str | None = None
    post_scan_json: str | None = None
    integrity_json: str | None = None
    explain_json: str | None = None
    pytest_ref: str | None = None
    bandit_ref: str | None = None
    harness_ref: str | None = None
    tree_hash_pre: str | None = None
    tree_hash_post: str | None = None
    failure_gate: str | None = None
    failure_reason: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None


@dataclass(frozen=True, slots=True)
class Event:
    job_id: str
    type: str
    severity: str
    title: str
    seq: int | None = None
    ts: str = field(default_factory=utcnow_iso)
    attempt: int | None = None
    message: str | None = None
    data_json: str | None = None


@dataclass(frozen=True, slots=True)
class Artifact:
    hash: str
    kind: str
    bytes: int
    content: str
    created_at: str = field(default_factory=utcnow_iso)


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    case_id: str
    job_id: str
    expected_decision: str
    id: int | None = None
    actual_decision: str | None = None
    attempts_used: int | None = None
    duration_ms: int | None = None
    correct: bool | None = None
    run_at: str = field(default_factory=utcnow_iso)


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    rule_id: str
    message: str
    path: str | None = None
    line: int | None = None


@dataclass(frozen=True, slots=True)
class DiffStats:
    files_changed: int
    lines_added: int
    lines_removed: int

    @property
    def changed_lines(self) -> int:
        return self.lines_added + self.lines_removed


@dataclass(frozen=True, slots=True)
class PolicyResult:
    violations: tuple[PolicyViolation, ...]
    stats: DiffStats

    @property
    def passed(self) -> bool:
        return not self.violations


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    passed: bool
    reason: str
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    security: EvidenceResult
    regression: EvidenceResult
    post_scan: EvidenceResult
    passed_test_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FailureEvidence:
    attempt: int
    failed_gate: str
    passed_gates: tuple[str, ...]
    headline: str
    detail: dict[str, object]
    previous_files: dict[str, str]
