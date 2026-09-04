from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Protocol

from backend.agent.llm_client import (
    ModelTechnicalError,
    PatchModel,
    PatchModelError,
    PatchProposal,
)
from backend.core.event_bus import EventBus
from backend.core.models import (
    Attempt,
    CandidateEvidence,
    EvidenceResult,
    Event,
    FailureEvidence,
    Finding,
    Job,
    PolicyResult,
    utcnow_iso,
)
from backend.core.states import JobState
from backend.core.workspace import WorkspaceManager
from backend.storage.repositories import AttemptRepo, FindingRepo, JobRepo
from backend.validator.pipeline import ValidatorPipeline
from backend.verification.gate import Verdict, evaluate
from backend.verification.integrity import IntegrityResult, compare, tree_hash


class FindingScanner(Protocol):
    async def scan(self, workspace: Path) -> tuple[Finding, ...]: ...


class CandidateVerifier(Protocol):
    async def reproduce(self, workspace: Path, finding: Finding) -> bool: ...

    async def verify(
        self,
        workspace: Path,
        finding: Finding,
        attempt_number: int,
    ) -> CandidateEvidence: ...


class Orchestrator:
    def __init__(
        self,
        *,
        jobs: JobRepo,
        attempts: AttemptRepo,
        findings: FindingRepo,
        events: EventBus,
        workspace: WorkspaceManager,
        validator: ValidatorPipeline,
        scanner: FindingScanner,
        model: PatchModel,
        verifier: CandidateVerifier,
    ) -> None:
        self.jobs = jobs
        self.attempts = attempts
        self.findings = findings
        self.events = events
        self.workspace = workspace
        self.validator = validator
        self.scanner = scanner
        self.model = model
        self.verifier = verifier

    async def run(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if job is None:
            raise KeyError(f"job not found: {job_id}")

        await self._emit(job, "job_created", "Job accepted")
        base = await asyncio.to_thread(
            self.workspace.materialize,
            job.repository_url,
            job.base_sha,
            job.id,
        )

        job = await self._transition(job, JobState.SCANNING)
        await self._emit(job, "scan_started", "Repository scan started")
        findings = await self.scanner.scan(base)
        await self._emit(
            job,
            "scan_completed",
            "Repository scan completed",
            data={"finding_count": len(findings)},
        )
        if not findings:
            return await self._terminal(
                job,
                JobState.ESCALATED,
                "escalated",
                "no_supported_finding",
            )

        finding = findings[0]
        self.findings.create(finding, job.id)
        job = await self._transition(job, JobState.FINDING_IDENTIFIED)
        await self._emit(
            job,
            "finding_detected",
            "Supported finding selected",
            severity="warning",
            data={"finding_id": finding.id, "rule_id": finding.rule_id},
        )

        job = await self._transition(job, JobState.REPRODUCING)
        await self._emit(job, "reproduction_started", "Reproduction started")
        if not await self.verifier.reproduce(base, finding):
            return await self._terminal(
                job,
                JobState.ESCALATED,
                "escalated",
                "not_reproduced",
            )
        job = await self._transition(job, JobState.REPRODUCED)
        await self._emit(
            job,
            "reproduction_confirmed",
            "Finding reproduced",
            severity="critical",
        )

        failure_evidence: FailureEvidence | None = None
        for attempt_number in range(1, job.max_attempts + 1):
            job = await self._transition(job, JobState.CONTEXT_BUILDING)
            job = await self._transition(job, JobState.GENERATING_PATCH)
            try:
                proposal = await self.model.generate_patch(
                    finding,
                    failure_evidence=failure_evidence,
                    report_technical_error=lambda error: self._report_model_error(
                        job,
                        error,
                    ),
                )
            except PatchModelError as exc:
                return await self._terminal(
                    job,
                    JobState.FAILED,
                    "failed",
                    str(exc),
                )
            attempt = self.attempts.create(
                Attempt(
                    job_id=job.id,
                    attempt_number=attempt_number,
                    model=self.model.name,
                    started_at=utcnow_iso(),
                )
            )
            await self._emit(
                job,
                "patch_generated",
                proposal.summary,
                attempt=attempt_number,
                data={"files": [file.path for file in proposal.files]},
            )

            job = await self._transition(
                job,
                JobState.VALIDATING_PATCH,
                current_attempt=attempt_number,
            )
            candidate = await asyncio.to_thread(
                self.workspace.apply_changes,
                job.id,
                attempt_number,
                {file.path: file.new_content for file in proposal.files},
            )
            try:
                policy = self.validator.run(base, candidate)
                if not policy.passed:
                    attempt = self._record_policy_rejection(attempt, proposal, policy)
                    await self._emit(
                        job,
                        "policy_failed",
                        "Candidate blocked by policy",
                        severity="critical",
                        attempt=attempt_number,
                        data={
                            "rules": [
                                violation.rule_id for violation in policy.violations
                            ]
                        },
                    )
                    if attempt_number == job.max_attempts:
                        return await self._terminal(
                            job,
                            JobState.POLICY_REJECTED,
                            "policy_rejected",
                            policy.violations[0].message,
                        )
                    failure_evidence = self._policy_failure(
                        attempt_number,
                        proposal,
                        policy,
                    )
                    job = await self._transition(job, JobState.RETRYING)
                    continue

                await self._emit(
                    job,
                    "policy_passed",
                    "Candidate passed static policy",
                    attempt=attempt_number,
                )
                pre_run = tree_hash(candidate)
                job = await self._transition(job, JobState.SANDBOXING)
                await self._emit(
                    job,
                    "sandbox_started",
                    "Candidate verification started",
                    attempt=attempt_number,
                )
                evidence = await self.verifier.verify(
                    candidate,
                    finding,
                    attempt_number,
                )
                post_run = tree_hash(candidate)
                await self._emit(
                    job,
                    "sandbox_completed",
                    "Candidate verification completed",
                    attempt=attempt_number,
                )

                job = await self._transition(job, JobState.VERIFYING_SECURITY)
                await self._emit_gate(job, "security", evidence.security, attempt_number)
                job = await self._transition(job, JobState.VERIFYING_REGRESSION)
                await self._emit_gate(
                    job,
                    "regression",
                    evidence.regression,
                    attempt_number,
                )
                job = await self._transition(job, JobState.POST_SCANNING)
                await self._emit_gate(
                    job,
                    "post_scan",
                    evidence.post_scan,
                    attempt_number,
                )
                job = await self._transition(job, JobState.INTEGRITY_CHECK)
                delivery_hash = tree_hash(candidate)
                integrity = compare(pre_run, post_run, delivery_hash)
                await self._emit_gate(job, "integrity", integrity, attempt_number)
                await self._emit_gate(job, "explain", evidence.explain, attempt_number)

                verdict = evaluate(
                    policy=policy.passed,
                    security=evidence.security.passed,
                    regression=evidence.regression.passed,
                    post_scan=evidence.post_scan.passed,
                    integrity=integrity.passed,
                    explain=evidence.explain.passed,
                )
                self._record_verdict(
                    attempt,
                    proposal,
                    policy,
                    evidence,
                    integrity,
                    verdict,
                )

                if verdict.verified:
                    job = await self._transition(
                        job,
                        JobState.VERIFIED,
                        final_decision=verdict.decision,
                        final_reason=verdict.reason,
                    )
                    await self._emit(
                        job,
                        "verified",
                        verdict.reason,
                        severity="success",
                        attempt=attempt_number,
                    )
                    job = await self._transition(job, JobState.CREATING_PR)
                    return await self._transition(
                        job,
                        JobState.COMPLETED,
                        completed_at=utcnow_iso(),
                    )

                if not integrity.passed:
                    return await self._terminal(
                        job,
                        JobState.FAILED,
                        "failed",
                        integrity.reason,
                    )

                failure_evidence = self._gate_failure(
                    attempt_number,
                    proposal,
                    policy,
                    evidence,
                    integrity,
                    verdict,
                )
                job = await self._transition(job, JobState.RETRYING)
                await self._emit(
                    job,
                    "candidate_rejected",
                    verdict.reason,
                    severity="critical",
                    attempt=attempt_number,
                )
                if attempt_number == job.max_attempts:
                    return await self._terminal(
                        job,
                        JobState.ESCALATED,
                        "escalated",
                        "retry_budget_exhausted",
                    )
            finally:
                await asyncio.to_thread(self.workspace.cleanup_candidate, candidate)

        raise AssertionError("bounded attempt loop ended without a terminal state")

    def _record_policy_rejection(
        self,
        attempt: Attempt,
        proposal: PatchProposal,
        policy: PolicyResult,
    ) -> Attempt:
        recorded = replace(
            attempt,
            summary=proposal.summary,
            files_changed=policy.stats.files_changed,
            lines_added=policy.stats.lines_added,
            lines_removed=policy.stats.lines_removed,
            policy_json=json.dumps(asdict(policy), sort_keys=True),
            decision="rejected",
            failure_gate="policy",
            failure_reason=policy.violations[0].message,
            completed_at=utcnow_iso(),
        )
        return self.attempts.update(recorded)

    def _record_verdict(
        self,
        attempt: Attempt,
        proposal: PatchProposal,
        policy: PolicyResult,
        evidence: CandidateEvidence,
        integrity: IntegrityResult,
        verdict: Verdict,
    ) -> Attempt:
        recorded = replace(
            attempt,
            summary=proposal.summary,
            files_changed=policy.stats.files_changed,
            lines_added=policy.stats.lines_added,
            lines_removed=policy.stats.lines_removed,
            policy_json=json.dumps(asdict(policy), sort_keys=True),
            security_json=json.dumps(asdict(evidence.security), sort_keys=True),
            regression_json=json.dumps(asdict(evidence.regression), sort_keys=True),
            post_scan_json=json.dumps(asdict(evidence.post_scan), sort_keys=True),
            integrity_json=json.dumps(asdict(integrity), sort_keys=True),
            tree_hash_pre=integrity.pre_run,
            tree_hash_post=integrity.post_run,
            decision=verdict.decision,
            failure_gate=verdict.first_failure,
            failure_reason=None if verdict.verified else verdict.reason,
            completed_at=utcnow_iso(),
        )
        return self.attempts.update(recorded)

    @staticmethod
    def _policy_failure(
        attempt_number: int,
        proposal: PatchProposal,
        policy: PolicyResult,
    ) -> FailureEvidence:
        violation = policy.violations[0]
        return FailureEvidence(
            attempt=attempt_number,
            failed_gate="policy",
            passed_gates=(),
            headline=violation.message,
            detail=asdict(violation),
            previous_files={file.path: file.new_content for file in proposal.files},
        )

    @staticmethod
    def _gate_failure(
        attempt_number: int,
        proposal: PatchProposal,
        policy: PolicyResult,
        evidence: CandidateEvidence,
        integrity: IntegrityResult,
        verdict: Verdict,
    ) -> FailureEvidence:
        results = {
            "policy": (policy.passed, "static policy passed"),
            "security": (evidence.security.passed, evidence.security.reason),
            "regression": (evidence.regression.passed, evidence.regression.reason),
            "post_scan": (evidence.post_scan.passed, evidence.post_scan.reason),
            "integrity": (integrity.passed, integrity.reason),
            "explain": (evidence.explain.passed, evidence.explain.reason),
        }
        passed = tuple(name for name, (did_pass, _) in results.items() if did_pass)
        failed_gate = verdict.first_failure or "unknown"
        detail = {
            name: {"passed": did_pass, "reason": reason}
            for name, (did_pass, reason) in results.items()
            if not did_pass
        }
        return FailureEvidence(
            attempt=attempt_number,
            failed_gate=failed_gate,
            passed_gates=passed,
            headline=verdict.reason,
            detail=detail,
            previous_files={file.path: file.new_content for file in proposal.files},
        )

    async def _transition(
        self,
        job: Job,
        target: JobState,
        **changes: object,
    ) -> Job:
        updated = replace(
            job,
            state=target.value,
            updated_at=utcnow_iso(),
            **changes,
        )
        persisted = self.jobs.update(updated)
        await self._emit(
            persisted,
            "state_changed",
            f"Job entered {target.value}",
            data={"state": target.value},
        )
        return persisted

    async def _terminal(
        self,
        job: Job,
        state: JobState,
        decision: str,
        reason: str,
    ) -> Job:
        return await self._transition(
            job,
            state,
            final_decision=decision,
            final_reason=reason,
            completed_at=utcnow_iso(),
        )

    async def _emit_gate(
        self,
        job: Job,
        gate_name: str,
        result: EvidenceResult | IntegrityResult,
        attempt: int,
    ) -> None:
        await self._emit(
            job,
            f"{gate_name}_{'passed' if result.passed else 'failed'}",
            result.reason,
            severity="success" if result.passed else "warning",
            attempt=attempt,
        )

    async def _report_model_error(
        self,
        job: Job,
        error: ModelTechnicalError,
    ) -> None:
        await self._emit(
            job,
            "technical_error",
            error.message,
            severity="critical",
            data=asdict(error),
        )

    async def _emit(
        self,
        job: Job,
        event_type: str,
        title: str,
        *,
        severity: str = "info",
        attempt: int | None = None,
        data: dict[str, object] | None = None,
    ) -> None:
        await self.events.publish(
            Event(
                job_id=job.id,
                type=event_type,
                severity=severity,
                title=title,
                attempt=attempt,
                data_json=json.dumps(data, sort_keys=True) if data is not None else None,
            )
        )
