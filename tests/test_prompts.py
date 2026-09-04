from __future__ import annotations

from backend.agent.prompts import SYSTEM_PROMPT, render_patch_prompt
from backend.core.models import FailureEvidence, Finding


FINDING = Finding(
    id="AEGIS-SQL-RETRY",
    scanner="aegis-ast",
    rule_id="AEGIS-SQL-001",
    category="SQL_INJECTION",
    cwe="CWE-89",
    severity="HIGH",
    confidence="HIGH",
    file_path="app/database.py",
    line_start=69,
    line_end=73,
    symbol="search_users",
    message="query concatenates caller-controlled input",
)


def test_system_prompt_denies_model_control_plane_authority() -> None:
    assert "Your output is a proposal. It has no authority." in SYSTEM_PROMPT
    assert "oracles\nyou cannot see or modify" in SYSTEM_PROMPT
    assert "Do not modify tests" in SYSTEM_PROMPT
    assert "COMPLETE new contents" in SYSTEM_PROMPT


def test_first_attempt_prompt_contains_original_context_and_policy() -> None:
    prompt = render_patch_prompt(
        FINDING,
        '<untrusted_repository_content path="app/database.py">source</untrusted_repository_content>',
        '{"max_files_changed": 3}',
    )

    assert FINDING.id in prompt
    assert "independently reproduced" in prompt
    assert "ORIGINAL REPOSITORY CONTEXT" in prompt
    assert "source" in prompt
    assert '"max_files_changed": 3' in prompt
    assert "OUTPUT SCHEMA" in prompt
    assert "smallest valid patch" in prompt
    assert "previous candidate was REJECTED" not in prompt


def test_retry_prompt_uses_failure_evidence_and_repeats_original_source() -> None:
    evidence = FailureEvidence(
        attempt=1,
        failed_gate="regression",
        passed_gates=("policy", "security", "post_scan", "integrity"),
        headline="regression gate failed",
        detail={
            "test_id": "tests/test_database.py::test_search_partial_match",
            "expected": ["Alice Johnson", "Alicia Keys", "Alina Chen"],
            "actual": [],
            "failing_call": 'search_users("ali")',
        },
        previous_files={
            "app/database.py": "def search_users(term):\n    return []\n"
        },
    )

    prompt = render_patch_prompt(
        FINDING,
        '<untrusted_repository_content path="app/database.py">ORIGINAL_SOURCE</untrusted_repository_content>',
        '{"allow_test_modification": false}',
        evidence,
    )

    assert "previous candidate was REJECTED" in prompt
    assert "- security: PASS" in prompt
    assert "- gate: regression" in prompt
    assert "test_search_partial_match" in prompt
    assert 'search_users(\\"ali\\")' in prompt
    assert "return []" in prompt
    assert "ORIGINAL_SOURCE" in prompt
    assert "starting from the ORIGINAL repository context" in prompt
    assert "Preserve the security property" in prompt
