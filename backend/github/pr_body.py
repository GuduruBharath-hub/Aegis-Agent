from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from backend.core.models import Attempt, Finding, Job


_GATE_FIELDS = (
    ("Security oracle", "security_json"),
    ("Regression", "regression_json"),
    ("Post-patch scan", "post_scan_json"),
    ("Patch policy", "policy_json"),
    ("Artifact integrity", "integrity_json"),
    ("Explainability", "explain_json"),
)


def render_pr_body(
    *,
    job: Job,
    finding: Finding,
    attempts: Sequence[Attempt],
    verified_attempt: Attempt,
    diff: str,
    delivered_hash: str,
) -> str:
    """Render the evidence already persisted for the delivered candidate."""
    explanation = _object(verified_attempt.explain_json)
    rationale = _mapping(explanation.get("rationale"))
    rejected = [attempt for attempt in attempts if attempt.decision != "verified"]

    lines = [
        f"## AegisAgent Remediation — {_inline(job.id)}",
        "",
        (
            f"**{_inline(finding.cwe)} {_inline(finding.category.replace('_', ' ').title())}** "
            f"| {_inline(finding.severity)} | `{_code(finding.file_path)}:"
            f"{finding.line_start}` in `{_code(finding.symbol)}`"
        ),
        (
            f"Base commit `{_code(job.base_sha[:12])}` | Attempts used **"
            f"{verified_attempt.attempt_number} / {job.max_attempts}** | Sandbox tier "
            f"`{_code(job.sandbox_tier or 'configured')}`"
        ),
        "",
        "### What changed",
        "",
        _paragraph(verified_attempt.summary or "The verified candidate applies a minimal remediation."),
        "",
        (
            f"{verified_attempt.files_changed or 0} file(s) changed | "
            f"+{verified_attempt.lines_added or 0} "
            f"-{verified_attempt.lines_removed or 0}"
        ),
        "",
        "### Evidence",
        "",
        "| Gate | Result | Detail |",
        "|---|---|---|",
    ]
    for label, field in _GATE_FIELDS:
        evidence = _object(getattr(verified_attempt, field))
        result = "PASS" if evidence.get("passed") is True else "FAIL"
        lines.append(f"| {label} | **{result}** | {_table_detail(evidence)} |")

    if rejected:
        lines.extend(["", "### Earlier attempts rejected automatically"])
        for attempt in rejected:
            lines.extend(
                [
                    "",
                    f"#### Attempt {attempt.attempt_number}",
                    "",
                    _attempt_summary(attempt),
                ]
            )

    lines.extend(
        [
            "",
            "### Annotated diff",
            "",
            _diff_block(diff),
            "",
            "#### Why these lines changed",
            "",
        ]
    )
    line_rationales = _list_of_mappings(rationale.get("line_rationales"))
    if line_rationales:
        for item in line_rationales:
            changed_lines = ", ".join(str(line) for line in item.get("changed_lines", []))
            lines.append(
                f"- `{_code(str(item.get('path', 'unknown')))}:{_code(changed_lines)}` "
                f"({_inline(str(item.get('change_kind', 'other')))}) — "
                f"{_paragraph(str(item.get('why', 'No rationale supplied.')))} "
                f"Evidence: `{_code(str(item.get('earns', 'unresolved')))}`."
            )
    else:
        lines.append("- No line rationale was recorded.")

    lines.extend(
        [
            "",
            "### Reviewer brief",
            "",
            f"- **Vulnerability mechanism:** {_paragraph(str(rationale.get('vulnerability_mechanism', 'Not recorded.')))}",
            f"- **Fix mechanism:** {_paragraph(str(rationale.get('fix_mechanism', 'Not recorded.')))}",
        ]
    )
    checks = _strings(rationale.get("reviewer_must_confirm"))
    lines.append("- **Reviewer must confirm:**")
    lines.extend(f"  - {_paragraph(check)}" for check in checks)

    preserved = _list_of_mappings(rationale.get("behaviour_preservation"))
    if preserved:
        lines.append("- **Behaviour-preservation evidence:**")
        for item in preserved:
            lines.append(
                f"  - {_paragraph(str(item.get('behaviour', 'Behaviour')))} — proven by "
                f"`{_code(str(item.get('proven_by', 'unresolved')))}`."
            )

    alternatives = _list_of_mappings(rationale.get("rejected_alternatives"))
    if alternatives:
        lines.append("- **Rejected alternatives:**")
        for item in alternatives:
            lines.append(
                f"  - {_paragraph(str(item.get('approach', 'Alternative')))}: "
                f"{_paragraph(str(item.get('why_not', 'not selected')))}"
            )

    lines.extend(
        [
            "",
            "### What was NOT proven",
            "",
            "VERIFIED means this exact candidate satisfied the six configured gates "
            "against the recorded base commit. It does **not** prove that:",
            "",
            "- the application is free of other vulnerabilities;",
            "- unconfigured platforms, inputs, or deployment environments are safe;",
            "- dependencies or code outside the changed scope were audited; or",
            "- the patch is suitable to merge without human review.",
        ]
    )
    residual_risks = _strings(rationale.get("residual_risk"))
    if residual_risks:
        lines.extend(["", "Model-declared residual risks:"])
        lines.extend(f"- {_paragraph(risk)}" for risk in residual_risks)
    lines.extend(
        [
            "",
            (
                f"Integrity: verified `{_code(verified_attempt.tree_hash_pre or '')}` "
                f"and delivered `{_code(delivered_hash)}`."
            ),
            "",
            "**This PR requires human review. AegisAgent cannot merge it.**",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _attempt_summary(attempt: Attempt) -> str:
    passed: list[str] = []
    for label, field in _GATE_FIELDS:
        if _object(getattr(attempt, field)).get("passed") is True:
            passed.append(label)
    passed_text = ", ".join(passed) if passed else "No later gate was credited"
    reason = attempt.failure_reason or "candidate did not satisfy the configured gates"
    return (
        f"Passed before rejection: {_inline(passed_text)}. **Failed gate:** "
        f"`{_code(attempt.failure_gate or 'unknown')}` — {_paragraph(reason)}. "
        "The evidence was recorded and supplied to the next bounded attempt."
    )


def _table_detail(evidence: Mapping[str, Any]) -> str:
    reason = str(evidence.get("reason") or "recorded gate result")
    detail = _mapping(evidence.get("detail"))
    if detail:
        pairs = ", ".join(
            f"{key}={_compact(value)}" for key, value in sorted(detail.items())
        )
        reason = f"{reason}; {pairs}"
    if "stats" in evidence:
        stats = _mapping(evidence.get("stats"))
        if stats:
            reason = (
                f"{reason}; files={stats.get('files_changed', 0)}, "
                f"+{stats.get('lines_added', 0)} -{stats.get('lines_removed', 0)}"
            )
    return _table_cell(reason)


def _diff_block(diff: str) -> str:
    longest = max((len(match) for match in re.findall(r"`+", diff)), default=0)
    fence = "`" * max(4, longest + 1)
    return f"{fence}diff\n{diff.rstrip()}\n{fence}"


def _object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _compact(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _paragraph(value: str) -> str:
    return " ".join(value.split())


def _inline(value: str) -> str:
    return _paragraph(value).replace("|", "\\|")


def _table_cell(value: str) -> str:
    return _inline(value)


def _code(value: str) -> str:
    return value.replace("`", "'")
