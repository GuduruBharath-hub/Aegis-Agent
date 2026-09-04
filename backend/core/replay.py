from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
import hashlib
import hmac
import json
from pathlib import Path
import re
from typing import Any, TypeVar

from backend.core.models import Artifact, Attempt, Event, Finding, Job, utcnow_iso
from backend.core.states import JobState, TERMINAL
from backend.core.workspace import read_text, write_text
from backend.storage.repositories import (
    ArtifactRepo,
    AttemptRepo,
    EventRepo,
    FindingRepo,
    JobRepo,
)
from backend.verification.gate import evaluate


REPLAY_FORMAT_VERSION = 1
_SAFE_RECORDING_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_ARTIFACT_FIELDS = ("diff_ref", "pytest_ref", "bandit_ref", "harness_ref")
_T = TypeVar("_T")


class ReplayError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReplaySummary:
    id: str
    source_job_id: str
    scenario: str | None
    final_decision: str
    attempts: int
    event_count: int
    recorded_at: str


@dataclass(frozen=True, slots=True)
class ReplayRecording:
    summary: ReplaySummary
    job: Job
    findings: tuple[Finding, ...]
    attempts: tuple[Attempt, ...]
    artifacts: tuple[Artifact, ...]
    events: tuple[Event, ...]


class ReplayArchive:
    """Stores immutable snapshots of genuine terminal jobs as JSONL."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def write(self, recording: ReplayRecording) -> Path:
        _validate_recording(recording)
        path = self._path(recording.summary.id)
        if path.exists():
            raise ReplayError(f"replay recording already exists: {recording.summary.id}")

        records = [
            _record(
                "metadata",
                {
                    "format_version": REPLAY_FORMAT_VERSION,
                    "summary": asdict(recording.summary),
                    "job": asdict(recording.job),
                },
            ),
            *(_record("artifact", asdict(item)) for item in recording.artifacts),
            *(_record("finding", asdict(item)) for item in recording.findings),
            *(_record("attempt", asdict(item)) for item in recording.attempts),
            *(_record("event", asdict(item)) for item in recording.events),
        ]
        body = "\n".join(records) + "\n"
        checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
        write_text(path, body + _record("checksum", {"sha256": checksum}) + "\n")
        return path

    def load(self, recording_id: str) -> ReplayRecording:
        path = self._path(recording_id)
        if not path.is_file():
            raise ReplayError(f"replay recording not found: {recording_id}")
        lines = [line for line in read_text(path).splitlines() if line]
        if len(lines) < 3:
            raise ReplayError("replay recording is incomplete")

        checksum_record = _json_object(lines[-1])
        if checksum_record.get("type") != "checksum":
            raise ReplayError("replay recording has no checksum")
        checksum_payload = _object(checksum_record.get("payload"), "checksum payload")
        expected = checksum_payload.get("sha256")
        body = "\n".join(lines[:-1]) + "\n"
        actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if not isinstance(expected, str) or not hmac.compare_digest(expected, actual):
            raise ReplayError("replay recording checksum does not match")

        records = [_json_object(line) for line in lines[:-1]]
        metadata = records[0]
        if metadata.get("type") != "metadata":
            raise ReplayError("replay metadata must be the first record")
        payload = _object(metadata.get("payload"), "metadata payload")
        if payload.get("format_version") != REPLAY_FORMAT_VERSION:
            raise ReplayError("unsupported replay format version")

        recording = ReplayRecording(
            summary=_dataclass_from(
                ReplaySummary,
                _object(payload.get("summary"), "replay summary"),
            ),
            job=_dataclass_from(Job, _object(payload.get("job"), "recorded job")),
            artifacts=tuple(
                _dataclass_from(Artifact, item)
                for item in _payloads(records[1:], "artifact")
            ),
            findings=tuple(
                _dataclass_from(Finding, item)
                for item in _payloads(records[1:], "finding")
            ),
            attempts=tuple(
                _dataclass_from(Attempt, item)
                for item in _payloads(records[1:], "attempt")
            ),
            events=tuple(
                _dataclass_from(Event, item)
                for item in _payloads(records[1:], "event")
            ),
        )
        if recording.summary.id != recording_id:
            raise ReplayError("recording id does not match its filename")
        _validate_recording(recording)
        return recording

    def list(self) -> list[ReplaySummary]:
        if not self.root.is_dir():
            return []
        return [self.load(path.stem).summary for path in sorted(self.root.glob("*.jsonl"))]

    def _path(self, recording_id: str) -> Path:
        if _SAFE_RECORDING_ID.fullmatch(recording_id) is None:
            raise ReplayError(f"unsafe replay recording id: {recording_id!r}")
        path = (self.root / f"{recording_id}.jsonl").resolve()
        if path.parent != self.root:
            raise ReplayError("replay recording path escapes the replay directory")
        return path


def record_job(
    recording_id: str,
    job_id: str,
    *,
    archive: ReplayArchive,
    jobs: JobRepo,
    findings: FindingRepo,
    attempts: AttemptRepo,
    events: EventRepo,
    artifacts: ArtifactRepo,
) -> ReplaySummary:
    job = jobs.get(job_id)
    if job is None:
        raise ReplayError(f"job not found: {job_id}")
    if JobState(job.state) not in TERMINAL or job.final_decision is None:
        raise ReplayError("only terminal jobs with a final decision can be recorded")
    if job.mode == "replay":
        raise ReplayError("a replay cannot be recorded as a new real run")

    recorded_attempts = tuple(attempts.list_for_job(job_id))
    recorded_events = tuple(events.list_for_job(job_id))
    referenced_artifacts: dict[str, Artifact] = {}
    for attempt in recorded_attempts:
        for field_name in _ARTIFACT_FIELDS:
            reference = getattr(attempt, field_name)
            if reference is None or reference in referenced_artifacts:
                continue
            artifact = artifacts.get(reference)
            if artifact is None:
                raise ReplayError(f"recorded attempt references missing artifact: {reference}")
            referenced_artifacts[reference] = artifact

    summary = ReplaySummary(
        id=recording_id,
        source_job_id=job.id,
        scenario=job.scenario,
        final_decision=job.final_decision,
        attempts=job.current_attempt,
        event_count=len(recorded_events),
        recorded_at=utcnow_iso(),
    )
    archive.write(
        ReplayRecording(
            summary=summary,
            job=job,
            findings=tuple(findings.list_for_job(job_id)),
            attempts=recorded_attempts,
            artifacts=tuple(referenced_artifacts.values()),
            events=recorded_events,
        )
    )
    return summary


def restore_job(
    recording: ReplayRecording,
    job_id: str,
    *,
    jobs: JobRepo,
    findings: FindingRepo,
    attempts: AttemptRepo,
    events: EventRepo,
    artifacts: ArtifactRepo,
) -> Job:
    """Restore evidence without running the model, sandbox, or delivery path."""
    now = utcnow_iso()
    replay_job = replace(
        recording.job,
        id=job_id,
        mode="replay",
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    jobs.create(replay_job)
    for artifact in recording.artifacts:
        artifacts.create(artifact)
    for finding in recording.findings:
        findings.create(finding, job_id)
    for attempt in recording.attempts:
        attempts.create(replace(attempt, job_id=job_id))
    for event in recording.events:
        events.create(replace(event, job_id=job_id, seq=None))
    return replay_job


def _validate_recording(recording: ReplayRecording) -> None:
    job = recording.job
    summary = recording.summary
    if job.mode == "replay":
        raise ReplayError("recording source must be a real live or demo run")
    if JobState(job.state) not in TERMINAL or job.final_decision is None:
        raise ReplayError("recorded job is not terminal")
    if summary.source_job_id != job.id:
        raise ReplayError("replay source job id does not match the recorded job")
    if summary.final_decision != job.final_decision:
        raise ReplayError("replay summary decision does not match the recorded job")
    if summary.attempts != job.current_attempt:
        raise ReplayError("replay summary attempt count does not match the recorded job")
    if summary.event_count != len(recording.events):
        raise ReplayError("replay summary event count does not match its event records")
    if any(item.job_id != job.id for item in (*recording.attempts, *recording.events)):
        raise ReplayError("recording contains evidence for a different job")
    terminal_states = [
        _event_state(event)
        for event in recording.events
        if event.type == "state_changed"
    ]
    if not terminal_states or terminal_states[-1] != job.state:
        raise ReplayError("recording does not end with its terminal state event")

    artifact_by_hash = {item.hash: item for item in recording.artifacts}
    for artifact in recording.artifacts:
        content = artifact.content.encode("utf-8")
        if hashlib.sha256(content).hexdigest() != artifact.hash or len(content) != artifact.bytes:
            raise ReplayError(f"recorded artifact failed integrity validation: {artifact.hash}")
    for attempt in recording.attempts:
        for field_name in _ARTIFACT_FIELDS:
            reference = getattr(attempt, field_name)
            if reference is not None and reference not in artifact_by_hash:
                raise ReplayError(f"recorded attempt references absent artifact: {reference}")

    if job.final_decision == "verified":
        verified_attempts = [item for item in recording.attempts if item.decision == "verified"]
        if not verified_attempts:
            raise ReplayError("verified recording has no verified attempt")
        attempt = verified_attempts[-1]
        verdict = evaluate(
            policy=_gate_passed(attempt.policy_json, policy=True),
            security=_gate_passed(attempt.security_json),
            regression=_gate_passed(attempt.regression_json),
            post_scan=_gate_passed(attempt.post_scan_json),
            integrity=_gate_passed(attempt.integrity_json),
            explain=_gate_passed(attempt.explain_json),
        )
        if not verdict.verified:
            raise ReplayError("recorded VERIFIED decision is not supported by all six gates")


def _gate_passed(value: str | None, *, policy: bool = False) -> bool:
    if value is None:
        return False
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, dict):
        return False
    passed = parsed.get("passed")
    if isinstance(passed, bool):
        return passed
    violations = parsed.get("violations")
    return policy and isinstance(violations, list) and not violations


def _event_state(event: Event) -> str | None:
    if event.data_json is None:
        return None
    try:
        data = json.loads(event.data_json)
    except json.JSONDecodeError:
        return None
    state = data.get("state") if isinstance(data, dict) else None
    return state if isinstance(state, str) else None


def _record(record_type: str, payload: dict[str, Any]) -> str:
    return json.dumps(
        {"type": record_type, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_object(line: str) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ReplayError("replay recording contains malformed JSON") from exc
    return _object(value, "JSONL record")


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReplayError(f"{label} must be an object")
    return value


def _payloads(records: list[dict[str, Any]], record_type: str) -> list[dict[str, Any]]:
    return [
        _object(record.get("payload"), f"{record_type} payload")
        for record in records
        if record.get("type") == record_type
    ]


def _dataclass_from(cls: type[_T], payload: dict[str, Any]) -> _T:
    expected = {item.name for item in fields(cls)}
    extras = set(payload) - expected
    if extras:
        raise ReplayError(f"unexpected fields in {cls.__name__}: {', '.join(sorted(extras))}")
    try:
        return cls(**payload)
    except TypeError as exc:
        raise ReplayError(f"invalid {cls.__name__} record: {exc}") from exc
