from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re

from backend.agent.llm_client import PatchRationale
from backend.core.workspace import read_text
from backend.validator.diff_policy import compare_trees
from backend.validator.protected_paths import PathEscapeError, normalize_relative_path


LineKey = tuple[str, int]


@dataclass(frozen=True, slots=True)
class ExplainViolation:
    code: str
    path: str | None = None
    lines: tuple[int, ...] = ()
    value: str | None = None


@dataclass(frozen=True, slots=True)
class ExplainResult:
    passed: bool
    violations: tuple[ExplainViolation, ...]
    reason: str


def _base_id(node_id: str) -> str:
    """Strip pytest's parametrisation suffix: `t.py::f[1-Alice]` -> `t.py::f`."""
    head, sep, _ = node_id.partition("[")
    return head if sep else node_id


def _citable_test_ids(
    passed_test_ids: tuple[str, ...],
    failed_test_ids: tuple[str, ...],
) -> frozenset[str]:
    """Node ids a rationale may legitimately cite as proof.

    Pytest reports a parametrised test once per case
    (`...::test_get_user[1-Alice]`), but a model reading the source sees only
    the function. Requiring the exact instance id would reject correct
    citations of real, passing tests — a false rejection, which is as damaging
    to this project's claim as a false verification.

    So a bare function id is citable too, but only when *every* instance of it
    passed. If any case failed, the function as a whole did not hold and must
    not be usable as proof.
    """
    citable = set(passed_test_ids)
    failed_bases = {_base_id(node_id) for node_id in failed_test_ids}
    citable.update(
        _base_id(node_id)
        for node_id in passed_test_ids
        if _base_id(node_id) not in failed_bases
    )
    return frozenset(citable)


def evaluate(
    base: Path,
    candidate: Path,
    rationale: PatchRationale,
    *,
    passed_test_ids: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    failed_test_ids: tuple[str, ...] = (),
) -> ExplainResult:
    changed = changed_lines(base, candidate)
    covered = {
        (line_rationale.path.replace("\\", "/"), line)
        for line_rationale in rationale.line_rationales
        for line in line_rationale.changed_lines
    }
    violations: list[ExplainViolation] = []

    unexplained = changed - covered
    for path, lines in _group_lines(unexplained).items():
        violations.append(ExplainViolation("unexplained_lines", path, lines))

    phantom = covered - changed
    for path, lines in _group_lines(phantom).items():
        violations.append(
            ExplainViolation("rationale_for_unchanged_line", path, lines)
        )

    passed_tests = _citable_test_ids(passed_test_ids, failed_test_ids)
    for claim in rationale.behaviour_preservation:
        if claim.proven_by not in passed_tests:
            violations.append(
                ExplainViolation("uncitable_test", value=claim.proven_by)
            )

    resolved_evidence = set(evidence_refs)
    for line_rationale in rationale.line_rationales:
        if line_rationale.earns not in resolved_evidence:
            violations.append(
                ExplainViolation(
                    "dangling_evidence_ref",
                    path=line_rationale.path,
                    lines=line_rationale.changed_lines,
                    value=line_rationale.earns,
                )
            )

    for line_rationale in rationale.line_rationales:
        source = _candidate_source(
            candidate,
            line_rationale.path,
            line_rationale.changed_lines,
        )
        if len(line_rationale.why.split()) < 6 or _similarity(
            line_rationale.why,
            source,
        ) > 0.8:
            violations.append(
                ExplainViolation(
                    "restatement_not_reasoning",
                    path=line_rationale.path,
                    lines=line_rationale.changed_lines,
                )
            )

    if not rationale.reviewer_must_confirm:
        violations.append(ExplainViolation("empty_reviewer_checklist"))

    return ExplainResult(
        passed=not violations,
        violations=tuple(violations),
        reason=(
            "rationale is complete and all citations resolve"
            if not violations
            else f"rationale failed {len(violations)} coverage check(s)"
        ),
    )


def changed_lines(base: Path, candidate: Path) -> set[LineKey]:
    changed: set[LineKey] = set()
    for file_change in compare_trees(base, candidate):
        candidate_path = candidate / Path(file_change.path)
        if not candidate_path.is_file() or file_change.binary:
            continue
        base_path = base / Path(file_change.path)
        before = read_text(base_path).splitlines() if base_path.is_file() else []
        after = read_text(candidate_path).splitlines()
        matcher = SequenceMatcher(None, before, after, autojunk=False)
        for operation, _, _, new_start, new_end in matcher.get_opcodes():
            if operation == "equal":
                continue
            changed.update(
                (file_change.path, line)
                for line in range(new_start + 1, new_end + 1)
            )
    return changed


def _candidate_source(candidate: Path, path: str, lines: tuple[int, ...]) -> str:
    try:
        normalized = normalize_relative_path(candidate, path)
    except PathEscapeError:
        return ""
    source_path = candidate / Path(normalized)
    if not source_path.is_file():
        return ""
    source_lines = read_text(source_path).splitlines()
    return "\n".join(
        source_lines[line - 1]
        for line in lines
        if 1 <= line <= len(source_lines)
    )


def _similarity(reason: str, source: str) -> float:
    token_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\S")
    reason_tokens = token_pattern.findall(reason.lower())
    source_tokens = token_pattern.findall(source.lower())
    if not reason_tokens or not source_tokens:
        return 0.0
    return SequenceMatcher(None, reason_tokens, source_tokens).ratio()


def _group_lines(values: set[LineKey]) -> dict[str, tuple[int, ...]]:
    grouped: dict[str, list[int]] = {}
    for path, line in sorted(values):
        grouped.setdefault(path, []).append(line)
    return {path: tuple(lines) for path, lines in grouped.items()}
