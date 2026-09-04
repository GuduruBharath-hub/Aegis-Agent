from __future__ import annotations

from pathlib import Path

import pytest

from backend.core.workspace import write_text
from backend.verification.gate import evaluate
from backend.verification.integrity import compare, tree_hash


def test_tree_hash_is_stable_for_lf_equivalent_content(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_text(first / "app.py", "alpha\r\nbeta\r")
    write_text(second / "app.py", "alpha\nbeta\n")

    assert tree_hash(first) == tree_hash(second)


@pytest.mark.parametrize(
    "excluded",
    [
        ".git/config",
        "_aegis_runtime/report.json",
        "pkg/__pycache__/module.pyc",
        "pkg/.pytest_cache/state",
    ],
)
def test_runtime_and_cache_files_are_outside_hash_domain(
    tmp_path: Path,
    excluded: str,
) -> None:
    workspace = tmp_path / "workspace"
    write_text(workspace / "app.py", "value = 1\n")
    before = tree_hash(workspace)

    write_text(workspace / excluded, "ephemeral content\n")

    assert tree_hash(workspace) == before


def test_included_file_change_alters_tree_hash(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_text(workspace / "app.py", "value = 1\n")
    before = tree_hash(workspace)

    write_text(workspace / "app.py", "value = 2\n")

    assert tree_hash(workspace) != before


def test_all_three_integrity_points_must_match() -> None:
    result = compare("same", "same", "same")

    assert result.passed is True
    assert result.reason == "all three tree hashes match"


@pytest.mark.parametrize(
    ("pre_run", "post_run", "delivery"),
    [
        ("h1", "changed-by-sandbox", "h1"),
        ("h1", "h1", "changed-before-delivery"),
        ("h1", "h2", "h3"),
    ],
)
def test_integrity_mismatch_blocks_verified_decision(
    pre_run: str,
    post_run: str,
    delivery: str,
) -> None:
    integrity = compare(pre_run, post_run, delivery)
    verdict = evaluate(
        policy=True,
        security=True,
        regression=True,
        post_scan=True,
        integrity=integrity.passed,
        explain=True,
    )

    assert integrity.passed is False
    assert verdict.verified is False
    assert verdict.first_failure == "integrity"
