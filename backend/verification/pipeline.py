from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.adapters import select_adapter
from backend.core.models import CandidateEvidence, EvidenceResult, Finding
from backend.sandbox.runner import SandboxRunner


class SandboxCandidateVerifier:
    """Translate sandbox reports into evidence without producing a verdict."""

    def __init__(self, runner: SandboxRunner) -> None:
        self.runner = runner
        self._image_ready = False
        self._image_lock = asyncio.Lock()

    async def reproduce(self, workspace: Path, finding: Finding) -> bool:
        await self._ensure_image()
        run = await asyncio.to_thread(
            self.runner.run,
            workspace,
            adapter=select_adapter(finding),
        )
        return bool(run.report.attack.get("exploited"))

    async def verify(
        self,
        workspace: Path,
        finding: Finding,
        attempt_number: int,
    ) -> CandidateEvidence:
        del attempt_number
        await self._ensure_image()
        run = await asyncio.to_thread(
            self.runner.run,
            workspace,
            adapter=select_adapter(finding),
        )
        attack = run.report.attack
        payloads = attack.get("payloads", [])
        payload_items = payloads if isinstance(payloads, list) else []
        attack_failures = sum(
            1
            for payload in payload_items
            if isinstance(payload, dict)
            and payload.get("kind") == "attack"
            and payload.get("exploited")
        )
        benign_failures = sum(
            1
            for payload in payload_items
            if isinstance(payload, dict)
            and payload.get("kind") == "benign"
            and not payload.get("passed")
        )
        security_passed = (
            not bool(attack.get("exploited"))
            and bool(attack.get("benign_preserved"))
        )

        pytest_report = run.report.pytest
        summary = pytest_report.get("summary", {})
        summary_values = summary if isinstance(summary, dict) else {}
        collected = int(summary_values.get("collected", 0))
        failed_count = int(summary_values.get("failed", 0)) + int(
            summary_values.get("error", 0)
        )
        passed_test_ids: list[str] = []
        failed_test_ids: list[str] = []
        failed_tests: list[dict[str, object]] = []
        tests = pytest_report.get("tests", [])
        for test in tests if isinstance(tests, list) else []:
            if not isinstance(test, dict):
                continue
            node_id = test.get("nodeid")
            if test.get("outcome") == "passed":
                if isinstance(node_id, str):
                    passed_test_ids.append(node_id)
                continue
            if isinstance(node_id, str):
                failed_test_ids.append(node_id)
            call = test.get("call", {})
            failed_tests.append(
                {
                    "test_id": node_id,
                    "outcome": test.get("outcome"),
                    "assertion": (
                        call.get("longrepr") if isinstance(call, dict) else None
                    ),
                }
            )
        regression_passed = collected > 0 and failed_count == 0

        bandit_results = run.report.bandit.get("results", [])
        findings = bandit_results if isinstance(bandit_results, list) else []
        original_bandit_rule = (
            "B602" if finding.category == "COMMAND_INJECTION" else "B608"
        )
        original_findings = [
            result
            for result in findings
            if isinstance(result, dict)
            and result.get("test_id") == original_bandit_rule
            and _normalized_path(result.get("filename")) == finding.file_path
        ]
        new_high_findings = [
            result
            for result in findings
            if isinstance(result, dict)
            and result.get("issue_severity") == "HIGH"
            and result not in original_findings
        ]
        post_scan_passed = not original_findings and not new_high_findings

        return CandidateEvidence(
            security=EvidenceResult(
                security_passed,
                (
                    "security and benign harness cases passed"
                    if security_passed
                    else "security or benign harness cases failed"
                ),
                {
                    "attack_failures": attack_failures,
                    "benign_failures": benign_failures,
                    "payloads_total": len(payload_items),
                },
            ),
            regression=EvidenceResult(
                regression_passed,
                (
                    f"all {collected} public tests passed"
                    if regression_passed
                    else f"{failed_count} of {collected} public tests failed"
                ),
                {
                    "collected": collected,
                    "failed_tests": failed_tests,
                },
            ),
            post_scan=EvidenceResult(
                post_scan_passed,
                (
                    "original finding absent and no new HIGH finding"
                    if post_scan_passed
                    else "post-patch scan found a blocking issue"
                ),
                {
                    "original_findings": len(original_findings),
                    "new_high_findings": len(new_high_findings),
                },
            ),
            passed_test_ids=tuple(passed_test_ids),
            failed_test_ids=tuple(failed_test_ids),
            evidence_refs=tuple(
                f"security.payload[{index}]"
                for index, payload in enumerate(payload_items)
                if isinstance(payload, dict)
            ),
            raw_pytest=json.dumps(pytest_report, indent=2, sort_keys=True),
            raw_bandit=json.dumps(run.report.bandit, indent=2, sort_keys=True),
            raw_harness=json.dumps(attack, indent=2, sort_keys=True),
        )

    async def _ensure_image(self) -> None:
        if self._image_ready:
            return
        async with self._image_lock:
            if not self._image_ready:
                await asyncio.to_thread(self.runner.ensure_image)
                self._image_ready = True


def _normalized_path(value: object) -> str:
    return str(value).replace("\\", "/").removeprefix("./")
