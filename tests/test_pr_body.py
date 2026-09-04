from __future__ import annotations

import json

from backend.core.models import Attempt, Finding, Job
from backend.github.pr_body import render_pr_body


def test_pr_body_carries_reviewable_evidence_and_limits_claim() -> None:
    job = Job(
        id="job-review",
        repository="demo",
        repository_url="https://github.invalid/example/demo",
        base_sha="a" * 40,
        mode="live",
        max_attempts=3,
        state="verified",
        current_attempt=2,
        sandbox_tier="docker",
        final_decision="verified",
    )
    finding = Finding(
        id="finding-1",
        scanner="bandit",
        rule_id="B608",
        category="SQL_INJECTION",
        cwe="CWE-89",
        severity="HIGH",
        confidence="HIGH",
        file_path="app/database.py",
        line_start=48,
        line_end=49,
        symbol="search_users",
        message="query includes untrusted input",
    )
    rejected = Attempt(
        job_id=job.id,
        attempt_number=1,
        decision="rejected",
        failure_gate="regression",
        failure_reason="partial matching test failed",
        security_json=json.dumps({"passed": True, "reason": "attacks blocked"}),
        regression_json=json.dumps({"passed": False, "reason": "one failed"}),
    )
    rationale = {
        "vulnerability_mechanism": "Input was concatenated into executable SQL.",
        "fix_mechanism": "Driver binding keeps input outside SQL grammar.",
        "line_rationales": [
            {
                "path": "app/database.py",
                "changed_lines": [48, 49],
                "change_kind": "parameterize",
                "why": "Binding prevents data from becoming executable syntax.",
                "earns": "security.payload[2]",
            }
        ],
        "behaviour_preservation": [
            {
                "behaviour": "partial matching",
                "preserved_by": "wildcards remain in the bound value",
                "proven_by": "tests/test_users.py::test_search_partial_match",
            }
        ],
        "rejected_alternatives": [
            {"approach": "strip quotes", "why_not": "breaks legitimate names"}
        ],
        "residual_risk": ["Other query call sites were not examined."],
        "reviewer_must_confirm": ["Confirm the driver uses bound parameters."],
    }
    verified = Attempt(
        job_id=job.id,
        attempt_number=2,
        decision="verified",
        summary="Bind the search term while preserving wildcard matching.",
        files_changed=1,
        lines_added=2,
        lines_removed=2,
        tree_hash_pre="b" * 64,
        security_json=json.dumps({"passed": True, "reason": "all payloads passed"}),
        regression_json=json.dumps({"passed": True, "reason": "18 tests passed"}),
        post_scan_json=json.dumps({"passed": True, "reason": "finding absent"}),
        policy_json=json.dumps(
            {
                "passed": True,
                "violations": [],
                "stats": {"files_changed": 1, "lines_added": 2, "lines_removed": 2},
            }
        ),
        integrity_json=json.dumps({"passed": True, "reason": "hashes match"}),
        explain_json=json.dumps(
            {"passed": True, "reason": "citations resolve", "rationale": rationale}
        ),
    )

    body = render_pr_body(
        job=job,
        finding=finding,
        attempts=(rejected, verified),
        verified_attempt=verified,
        diff="--- a/app/database.py\n+++ b/app/database.py\n@@ -48 +48 @@\n-old\n+new\n",
        delivered_hash="b" * 64,
    )

    assert "| Security oracle | **PASS** | all payloads passed |" in body
    assert "### Earlier attempts rejected automatically" in body
    assert "**Failed gate:** `regression`" in body
    assert "### Annotated diff" in body
    assert "`app/database.py:48, 49` (parameterize)" in body
    assert "### Reviewer brief" in body
    assert "tests/test_users.py::test_search_partial_match" in body
    assert "### What was NOT proven" in body
    assert "free of other vulnerabilities" in body
    assert "AegisAgent cannot merge it" in body


def test_pr_body_uses_longer_fence_when_diff_contains_backticks() -> None:
    attempt = Attempt(
        job_id="job-fence",
        attempt_number=1,
        decision="verified",
        tree_hash_pre="hash",
        policy_json='{"passed":true}',
        security_json='{"passed":true}',
        regression_json='{"passed":true}',
        post_scan_json='{"passed":true}',
        integrity_json='{"passed":true}',
        explain_json='{"passed":true,"rationale":{}}',
    )
    body = render_pr_body(
        job=Job("job-fence", "demo", "url", "sha", "live", 1),
        finding=Finding(
            "finding", "scanner", "rule", "category", "CWE-1", "HIGH", "HIGH",
            "app.py", 1, 1, "symbol", "message",
        ),
        attempts=(attempt,),
        verified_attempt=attempt,
        diff="+value = ```",
        delivered_hash="hash",
    )

    assert "````diff\n+value = ```\n````" in body
