from __future__ import annotations

from dataclasses import replace
import hashlib
import sqlite3

from backend.core.models import Artifact, Attempt, BenchmarkRun, Event, Finding, Job
from backend.core.states import validate_job_update


# --- Pragmas ---
PRAGMA_FOREIGN_KEYS_ON = "PRAGMA foreign_keys = ON;"
PRAGMA_JOURNAL_MODE_WAL = "PRAGMA journal_mode = WAL;"
PRAGMA_FOREIGN_KEYS_CHECK = "PRAGMA foreign_keys;"
PRAGMA_JOURNAL_MODE_CHECK = "PRAGMA journal_mode;"
PRAGMA_USER_VERSION = "PRAGMA user_version;"
PRAGMA_SET_USER_VERSION_1 = "PRAGMA user_version = 1;"
PRAGMA_SET_USER_VERSION_2 = "PRAGMA user_version = 2;"

MIGRATION_001_INITIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    repository      TEXT NOT NULL,
    repository_url  TEXT NOT NULL,
    base_sha        TEXT NOT NULL,
    mode            TEXT NOT NULL,
    scenario        TEXT,
    state           TEXT NOT NULL,
    current_attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL,
    sandbox_tier    TEXT,
    final_decision  TEXT,
    final_reason    TEXT,
    branch_name     TEXT,
    pr_url          TEXT,
    pr_number       INTEGER,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    hash       TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,
    bytes      INTEGER NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id          TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    scanner     TEXT,
    rule_id     TEXT,
    category    TEXT,
    cwe         TEXT,
    severity    TEXT,
    confidence  TEXT,
    file_path   TEXT,
    line_start  INTEGER,
    line_end    INTEGER,
    symbol      TEXT,
    message     TEXT,
    raw_ref     TEXT REFERENCES artifacts(hash),
    reproduced  INTEGER,
    repro_ref   TEXT REFERENCES artifacts(hash)
);

CREATE TABLE IF NOT EXISTS attempts (
    job_id            TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    attempt_number    INTEGER NOT NULL,
    model             TEXT,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    summary           TEXT,
    files_changed     INTEGER,
    lines_added       INTEGER,
    lines_removed     INTEGER,
    diff_ref          TEXT REFERENCES artifacts(hash),
    policy_json       TEXT,
    security_json     TEXT,
    regression_json   TEXT,
    post_scan_json    TEXT,
    integrity_json    TEXT,
    pytest_ref        TEXT,
    bandit_ref        TEXT,
    harness_ref       TEXT,
    tree_hash_pre     TEXT,
    tree_hash_post    TEXT,
    decision          TEXT NOT NULL,
    failure_gate      TEXT,
    failure_reason    TEXT,
    started_at        TEXT,
    completed_at      TEXT,
    duration_ms       INTEGER,
    PRIMARY KEY (job_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS events (
    seq       INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id    TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    ts        TEXT NOT NULL,
    type      TEXT NOT NULL,
    severity  TEXT NOT NULL,
    attempt   INTEGER,
    title     TEXT NOT NULL,
    message   TEXT,
    data_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_job_seq ON events(job_id, seq);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id           TEXT NOT NULL,
    job_id            TEXT NOT NULL,
    expected_decision TEXT NOT NULL,
    actual_decision   TEXT,
    attempts_used     INTEGER,
    duration_ms       INTEGER,
    correct           INTEGER,
    run_at            TEXT NOT NULL
);
"""

MIGRATION_002_EXPLAIN_RESULT = """
ALTER TABLE attempts ADD COLUMN explain_json TEXT;
"""

MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (1, MIGRATION_001_INITIAL_SCHEMA, PRAGMA_SET_USER_VERSION_1),
    (2, MIGRATION_002_EXPLAIN_RESULT, PRAGMA_SET_USER_VERSION_2),
)

SQL_SELECT_SCHEMA_TABLES = """
SELECT name
FROM sqlite_master
WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
ORDER BY name ASC;
"""


def apply_pragmas(conn: sqlite3.Connection) -> None:
    """Enable WAL mode and foreign-key enforcement for the connection."""
    conn.execute(PRAGMA_FOREIGN_KEYS_ON)
    conn.execute(PRAGMA_JOURNAL_MODE_WAL)


def is_foreign_keys_enabled(conn: sqlite3.Connection) -> bool:
    """Return whether foreign key constraints are enabled on this connection."""
    cursor = conn.execute(PRAGMA_FOREIGN_KEYS_CHECK)
    row = cursor.fetchone()
    return bool(row[0]) if row else False


def get_journal_mode(conn: sqlite3.Connection) -> str:
    """Return the active journal mode (e.g. 'wal' or 'memory')."""
    cursor = conn.execute(PRAGMA_JOURNAL_MODE_CHECK)
    row = cursor.fetchone()
    return str(row[0]).lower() if row else ""


def run_migrations(conn: sqlite3.Connection) -> list[int]:
    """Execute unapplied numbered migrations sequentially and return applied versions."""
    row = conn.execute(PRAGMA_USER_VERSION).fetchone()
    current_version = int(row[0]) if row is not None else 0
    newly_applied: list[int] = []

    for version, sql, version_sql in MIGRATIONS:
        if version > current_version:
            with conn:
                conn.executescript(sql)
                conn.execute(version_sql)
            newly_applied.append(version)
            current_version = version

    return newly_applied


def list_schema_tables(conn: sqlite3.Connection) -> tuple[str, ...]:
    cursor = conn.execute(SQL_SELECT_SCHEMA_TABLES)
    return tuple(str(row[0]) for row in cursor.fetchall())


# --- Job SQL Statements ---
SQL_INSERT_JOB = """
INSERT INTO jobs (
    id, repository, repository_url, base_sha, mode, scenario,
    state, current_attempt, max_attempts, sandbox_tier,
    final_decision, final_reason, branch_name, pr_url, pr_number,
    created_at, updated_at, completed_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

SQL_SELECT_JOB_BY_ID = """
SELECT
    id, repository, repository_url, base_sha, mode, scenario,
    state, current_attempt, max_attempts, sandbox_tier,
    final_decision, final_reason, branch_name, pr_url, pr_number,
    created_at, updated_at, completed_at
FROM jobs
WHERE id = ?;
"""

SQL_UPDATE_JOB = """
UPDATE jobs SET
    repository = ?,
    repository_url = ?,
    base_sha = ?,
    mode = ?,
    scenario = ?,
    state = ?,
    current_attempt = ?,
    max_attempts = ?,
    sandbox_tier = ?,
    final_decision = ?,
    final_reason = ?,
    branch_name = ?,
    pr_url = ?,
    pr_number = ?,
    updated_at = ?,
    completed_at = ?
WHERE id = ?;
"""

SQL_SELECT_ALL_JOBS = """
SELECT
    id, repository, repository_url, base_sha, mode, scenario,
    state, current_attempt, max_attempts, sandbox_tier,
    final_decision, final_reason, branch_name, pr_url, pr_number,
    created_at, updated_at, completed_at
FROM jobs
ORDER BY created_at DESC;
"""

SQL_DELETE_JOB = """
DELETE FROM jobs WHERE id = ?;
"""


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        repository=row["repository"],
        repository_url=row["repository_url"],
        base_sha=row["base_sha"],
        mode=row["mode"],
        scenario=row["scenario"],
        state=row["state"],
        current_attempt=row["current_attempt"],
        max_attempts=row["max_attempts"],
        sandbox_tier=row["sandbox_tier"],
        final_decision=row["final_decision"],
        final_reason=row["final_reason"],
        branch_name=row["branch_name"],
        pr_url=row["pr_url"],
        pr_number=row["pr_number"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


class JobRepo:
    """Repository for persisting and retrieving Job domain models."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, job: Job) -> Job:
        self._conn.execute(
            SQL_INSERT_JOB,
            (
                job.id,
                job.repository,
                job.repository_url,
                job.base_sha,
                job.mode,
                job.scenario,
                job.state,
                job.current_attempt,
                job.max_attempts,
                job.sandbox_tier,
                job.final_decision,
                job.final_reason,
                job.branch_name,
                job.pr_url,
                job.pr_number,
                job.created_at,
                job.updated_at,
                job.completed_at,
            ),
        )
        self._conn.commit()
        return job

    def get(self, job_id: str) -> Job | None:
        cursor = self._conn.execute(SQL_SELECT_JOB_BY_ID, (job_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_job(row)

    def update(self, job: Job) -> Job:
        current = self.get(job.id)
        if current is None:
            raise KeyError(f"job not found: {job.id}")
        validate_job_update(current, job)

        self._conn.execute(
            SQL_UPDATE_JOB,
            (
                job.repository,
                job.repository_url,
                job.base_sha,
                job.mode,
                job.scenario,
                job.state,
                job.current_attempt,
                job.max_attempts,
                job.sandbox_tier,
                job.final_decision,
                job.final_reason,
                job.branch_name,
                job.pr_url,
                job.pr_number,
                job.updated_at,
                job.completed_at,
                job.id,
            ),
        )
        self._conn.commit()
        return job

    def list_all(self) -> list[Job]:
        cursor = self._conn.execute(SQL_SELECT_ALL_JOBS)
        return [_row_to_job(row) for row in cursor.fetchall()]

    def delete(self, job_id: str) -> bool:
        cursor = self._conn.execute(SQL_DELETE_JOB, (job_id,))
        self._conn.commit()
        return cursor.rowcount > 0


# --- Attempt SQL Statements ---
SQL_INSERT_ATTEMPT = """
INSERT INTO attempts (
    job_id, attempt_number, model, prompt_tokens, completion_tokens,
    summary, files_changed, lines_added, lines_removed,
    diff_ref, policy_json, security_json, regression_json,
    post_scan_json, integrity_json, explain_json, pytest_ref, bandit_ref,
    harness_ref, tree_hash_pre, tree_hash_post, decision,
    failure_gate, failure_reason, started_at, completed_at, duration_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

SQL_SELECT_ATTEMPT = """
SELECT
    job_id, attempt_number, model, prompt_tokens, completion_tokens,
    summary, files_changed, lines_added, lines_removed,
    diff_ref, policy_json, security_json, regression_json,
    post_scan_json, integrity_json, explain_json, pytest_ref, bandit_ref,
    harness_ref, tree_hash_pre, tree_hash_post, decision,
    failure_gate, failure_reason, started_at, completed_at, duration_ms
FROM attempts
WHERE job_id = ? AND attempt_number = ?;
"""

SQL_SELECT_ATTEMPTS_FOR_JOB = """
SELECT
    job_id, attempt_number, model, prompt_tokens, completion_tokens,
    summary, files_changed, lines_added, lines_removed,
    diff_ref, policy_json, security_json, regression_json,
    post_scan_json, integrity_json, explain_json, pytest_ref, bandit_ref,
    harness_ref, tree_hash_pre, tree_hash_post, decision,
    failure_gate, failure_reason, started_at, completed_at, duration_ms
FROM attempts
WHERE job_id = ?
ORDER BY attempt_number ASC;
"""

SQL_UPDATE_ATTEMPT = """
UPDATE attempts SET
    model = ?,
    prompt_tokens = ?,
    completion_tokens = ?,
    summary = ?,
    files_changed = ?,
    lines_added = ?,
    lines_removed = ?,
    diff_ref = ?,
    policy_json = ?,
    security_json = ?,
    regression_json = ?,
    post_scan_json = ?,
    integrity_json = ?,
    explain_json = ?,
    pytest_ref = ?,
    bandit_ref = ?,
    harness_ref = ?,
    tree_hash_pre = ?,
    tree_hash_post = ?,
    decision = ?,
    failure_gate = ?,
    failure_reason = ?,
    started_at = ?,
    completed_at = ?,
    duration_ms = ?
WHERE job_id = ? AND attempt_number = ?;
"""


def _row_to_attempt(row: sqlite3.Row) -> Attempt:
    return Attempt(
        job_id=row["job_id"],
        attempt_number=row["attempt_number"],
        decision=row["decision"],
        model=row["model"],
        prompt_tokens=row["prompt_tokens"],
        completion_tokens=row["completion_tokens"],
        summary=row["summary"],
        files_changed=row["files_changed"],
        lines_added=row["lines_added"],
        lines_removed=row["lines_removed"],
        diff_ref=row["diff_ref"],
        policy_json=row["policy_json"],
        security_json=row["security_json"],
        regression_json=row["regression_json"],
        post_scan_json=row["post_scan_json"],
        integrity_json=row["integrity_json"],
        explain_json=row["explain_json"],
        pytest_ref=row["pytest_ref"],
        bandit_ref=row["bandit_ref"],
        harness_ref=row["harness_ref"],
        tree_hash_pre=row["tree_hash_pre"],
        tree_hash_post=row["tree_hash_post"],
        failure_gate=row["failure_gate"],
        failure_reason=row["failure_reason"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        duration_ms=row["duration_ms"],
    )


class AttemptRepo:
    """Repository for managing attempt execution and gate verdicts."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, attempt: Attempt) -> Attempt:
        self._conn.execute(
            SQL_INSERT_ATTEMPT,
            (
                attempt.job_id,
                attempt.attempt_number,
                attempt.model,
                attempt.prompt_tokens,
                attempt.completion_tokens,
                attempt.summary,
                attempt.files_changed,
                attempt.lines_added,
                attempt.lines_removed,
                attempt.diff_ref,
                attempt.policy_json,
                attempt.security_json,
                attempt.regression_json,
                attempt.post_scan_json,
                attempt.integrity_json,
                attempt.explain_json,
                attempt.pytest_ref,
                attempt.bandit_ref,
                attempt.harness_ref,
                attempt.tree_hash_pre,
                attempt.tree_hash_post,
                attempt.decision,
                attempt.failure_gate,
                attempt.failure_reason,
                attempt.started_at,
                attempt.completed_at,
                attempt.duration_ms,
            ),
        )
        self._conn.commit()
        return attempt

    def get(self, job_id: str, attempt_number: int) -> Attempt | None:
        cursor = self._conn.execute(
            SQL_SELECT_ATTEMPT,
            (job_id, attempt_number),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_attempt(row)

    def update(self, attempt: Attempt) -> Attempt:
        self._conn.execute(
            SQL_UPDATE_ATTEMPT,
            (
                attempt.model,
                attempt.prompt_tokens,
                attempt.completion_tokens,
                attempt.summary,
                attempt.files_changed,
                attempt.lines_added,
                attempt.lines_removed,
                attempt.diff_ref,
                attempt.policy_json,
                attempt.security_json,
                attempt.regression_json,
                attempt.post_scan_json,
                attempt.integrity_json,
                attempt.explain_json,
                attempt.pytest_ref,
                attempt.bandit_ref,
                attempt.harness_ref,
                attempt.tree_hash_pre,
                attempt.tree_hash_post,
                attempt.decision,
                attempt.failure_gate,
                attempt.failure_reason,
                attempt.started_at,
                attempt.completed_at,
                attempt.duration_ms,
                attempt.job_id,
                attempt.attempt_number,
            ),
        )
        self._conn.commit()
        return attempt

    def list_for_job(self, job_id: str) -> list[Attempt]:
        cursor = self._conn.execute(SQL_SELECT_ATTEMPTS_FOR_JOB, (job_id,))
        return [_row_to_attempt(row) for row in cursor.fetchall()]


# --- Event SQL Statements ---
SQL_INSERT_EVENT = """
INSERT INTO events (
    job_id, ts, type, severity, attempt, title, message, data_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""

SQL_SELECT_EVENT_BY_SEQ = """
SELECT
    seq, job_id, ts, type, severity, attempt, title, message, data_json
FROM events
WHERE seq = ?;
"""

SQL_SELECT_EVENTS_FOR_JOB = """
SELECT
    seq, job_id, ts, type, severity, attempt, title, message, data_json
FROM events
WHERE job_id = ? AND seq > ?
ORDER BY seq ASC;
"""

SQL_SELECT_ALL_EVENTS = """
SELECT
    seq, job_id, ts, type, severity, attempt, title, message, data_json
FROM events
WHERE seq > ?
ORDER BY seq ASC;
"""


def _row_to_event(row: sqlite3.Row) -> Event:
    return Event(
        seq=row["seq"],
        job_id=row["job_id"],
        ts=row["ts"],
        type=row["type"],
        severity=row["severity"],
        attempt=row["attempt"],
        title=row["title"],
        message=row["message"],
        data_json=row["data_json"],
    )


class EventRepo:
    """Repository for persisting sequential audit and streaming events."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, event: Event) -> Event:
        cursor = self._conn.execute(
            SQL_INSERT_EVENT,
            (
                event.job_id,
                event.ts,
                event.type,
                event.severity,
                event.attempt,
                event.title,
                event.message,
                event.data_json,
            ),
        )
        seq = cursor.lastrowid
        self._conn.commit()
        return replace(event, seq=seq)

    def get(self, seq: int) -> Event | None:
        cursor = self._conn.execute(SQL_SELECT_EVENT_BY_SEQ, (seq,))
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_event(row)

    def list_for_job(self, job_id: str, *, since_seq: int = 0) -> list[Event]:
        cursor = self._conn.execute(SQL_SELECT_EVENTS_FOR_JOB, (job_id, since_seq))
        return [_row_to_event(row) for row in cursor.fetchall()]

    def list_all(self, *, since_seq: int = 0) -> list[Event]:
        cursor = self._conn.execute(SQL_SELECT_ALL_EVENTS, (since_seq,))
        return [_row_to_event(row) for row in cursor.fetchall()]


# --- Artifact SQL Statements ---
SQL_INSERT_ARTIFACT = """
INSERT INTO artifacts (hash, kind, bytes, content, created_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(hash) DO NOTHING;
"""

SQL_SELECT_ARTIFACT_BY_HASH = """
SELECT hash, kind, bytes, content, created_at
FROM artifacts
WHERE hash = ?;
"""


def _row_to_artifact(row: sqlite3.Row) -> Artifact:
    return Artifact(
        hash=row["hash"],
        kind=row["kind"],
        bytes=row["bytes"],
        content=row["content"],
        created_at=row["created_at"],
    )


class ArtifactRepo:
    """Repository for content-addressed large blobs (diffs, reports, test logs)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, artifact: Artifact) -> Artifact:
        self._conn.execute(
            SQL_INSERT_ARTIFACT,
            (
                artifact.hash,
                artifact.kind,
                artifact.bytes,
                artifact.content,
                artifact.created_at,
            ),
        )
        self._conn.commit()
        return artifact

    def put(self, kind: str, content: str) -> Artifact:
        content_bytes = content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        artifact = Artifact(
            hash=content_hash,
            kind=kind,
            bytes=len(content_bytes),
            content=content,
        )
        self.create(artifact)
        return artifact

    def get(self, hash_val: str) -> Artifact | None:
        cursor = self._conn.execute(SQL_SELECT_ARTIFACT_BY_HASH, (hash_val,))
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_artifact(row)


# --- Finding SQL Statements ---
SQL_INSERT_FINDING = """
INSERT INTO findings (
    id, job_id, scanner, rule_id, category, cwe, severity, confidence,
    file_path, line_start, line_end, symbol, message, raw_ref, reproduced, repro_ref
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

SQL_SELECT_FINDINGS_FOR_JOB = """
SELECT
    id, job_id, scanner, rule_id, category, cwe, severity, confidence,
    file_path, line_start, line_end, symbol, message, raw_ref, reproduced, repro_ref
FROM findings
WHERE job_id = ?;
"""


class FindingRepo:
    """Repository for normalized security findings linked to jobs."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        finding: Finding,
        job_id: str,
        raw_ref: str | None = None,
        reproduced: int | None = None,
        repro_ref: str | None = None,
    ) -> Finding:
        self._conn.execute(
            SQL_INSERT_FINDING,
            (
                finding.id,
                job_id,
                finding.scanner,
                finding.rule_id,
                finding.category,
                finding.cwe,
                finding.severity,
                finding.confidence,
                finding.file_path,
                finding.line_start,
                finding.line_end,
                finding.symbol,
                finding.message,
                raw_ref,
                reproduced,
                repro_ref,
            ),
        )
        self._conn.commit()
        return finding

    def list_for_job(self, job_id: str) -> list[Finding]:
        cursor = self._conn.execute(SQL_SELECT_FINDINGS_FOR_JOB, (job_id,))
        findings: list[Finding] = []
        for row in cursor.fetchall():
            findings.append(
                Finding(
                    id=row["id"],
                    scanner=row["scanner"],
                    rule_id=row["rule_id"],
                    category=row["category"],
                    cwe=row["cwe"],
                    severity=row["severity"],
                    confidence=row["confidence"],
                    file_path=row["file_path"],
                    line_start=row["line_start"],
                    line_end=row["line_end"],
                    symbol=row["symbol"],
                    message=row["message"],
                )
            )
        return findings
