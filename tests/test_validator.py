from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil

import pytest

from backend.core.workspace import write_text
from backend.validator.pipeline import ValidatorPipeline, ValidatorPolicy
from backend.validator.protected_paths import PathEscapeError, normalize_relative_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY = ValidatorPolicy.from_file(PROJECT_ROOT / "policies" / "security_policy.json")


def _trees(tmp_path: Path, files: dict[str, str]) -> tuple[Path, Path]:
    base = tmp_path / "base"
    base.mkdir()
    for relative, content in files.items():
        write_text(base / relative, content)
    candidate = tmp_path / "candidate"
    shutil.copytree(base, candidate)
    return base, candidate


def _rule_ids(base: Path, candidate: Path, policy: ValidatorPolicy = POLICY) -> list[str]:
    return [
        violation.rule_id
        for violation in ValidatorPipeline(policy).run(base, candidate).violations
    ]


@pytest.mark.parametrize(
    "untrusted",
    ["../outside.py", r"..\outside.py"],
)
def test_relative_path_escape_is_rejected(tmp_path: Path, untrusted: str) -> None:
    with pytest.raises(PathEscapeError):
        normalize_relative_path(tmp_path / "workspace", untrusted)


def test_absolute_path_is_rejected(tmp_path: Path) -> None:
    absolute = (tmp_path / "workspace" / "app.py").resolve()
    with pytest.raises(PathEscapeError):
        normalize_relative_path(tmp_path / "workspace", absolute)


def test_symlink_escape_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.py"
    write_text(outside, "safe = True\n")
    link = workspace / "alias.py"
    try:
        link.symlink_to(outside)
    except OSError:
        original_resolve = Path.resolve

        def resolve_with_simulated_link(
            path: Path,
            strict: bool = False,
        ) -> Path:
            if path.absolute() == link.absolute():
                return outside.absolute()
            return original_resolve(path, strict=strict)

        # Windows commonly denies symlink creation without Developer Mode;
        # simulating its resolved target still exercises the containment check.
        monkeypatch.setattr(Path, "resolve", resolve_with_simulated_link)

    with pytest.raises(PathEscapeError):
        normalize_relative_path(workspace, "alias.py")


@pytest.mark.parametrize(
    "relative",
    [
        "aegis_hidden_tests/oracle.py",
        "_aegis_runtime/report.json",
        "policies/security_policy.json",
        ".github/workflows/ci.yml",
        "backend/sandbox/payload/run_all.py",
        "conftest.py",
        "tests/unit/test_app.py",
        "pytest.ini",
        "nested/pyproject.toml",
        "nested/requirements-dev.txt",
    ],
)
def test_each_protected_path_pattern_blocks_changes(
    tmp_path: Path,
    relative: str,
) -> None:
    base, candidate = _trees(tmp_path, {relative: "value = 1\n"})
    write_text(candidate / relative, "value = 2\n")

    assert "protected_path" in _rule_ids(base, candidate)


def test_pipeline_reports_syntax_before_protected_path(tmp_path: Path) -> None:
    base, candidate = _trees(tmp_path, {"tests/locked.py": "value = 1\n"})
    write_text(candidate / "tests/locked.py", "def broken(:\n")

    rule_ids = _rule_ids(base, candidate)

    assert rule_ids[:2] == ["syntax_error", "protected_path"]


@pytest.mark.parametrize("module", POLICY.denied_imports)
def test_every_denied_import_is_blocked(tmp_path: Path, module: str) -> None:
    base, candidate = _trees(tmp_path, {"app.py": "value = 1\n"})
    write_text(candidate / "app.py", f"import {module}\nvalue = 1\n")

    assert "denied_import" in _rule_ids(base, candidate)


def _symbol_source(symbol: str) -> str:
    if "." not in symbol:
        return f"def run(value):\n    return {symbol}(value)\n"
    module, attribute = symbol.split(".", 1)
    return f"import {module}\ndef run(value):\n    return {module}.{attribute}(value)\n"


@pytest.mark.parametrize("symbol", POLICY.denied_symbols)
def test_every_denied_symbol_is_blocked(tmp_path: Path, symbol: str) -> None:
    base, candidate = _trees(
        tmp_path,
        {"app.py": "def run(value):\n    return value\n"},
    )
    write_text(candidate / "app.py", _symbol_source(symbol))

    assert "denied_symbol" in _rule_ids(base, candidate)


def test_aliased_denied_symbol_is_blocked(tmp_path: Path) -> None:
    base, candidate = _trees(tmp_path, {"app.py": "value = 1\n"})
    write_text(
        candidate / "app.py",
        "import os as operating_system\noperating_system.system('whoami')\n",
    )

    assert "denied_symbol" in _rule_ids(base, candidate)


def test_file_count_limit_accepts_boundary_and_rejects_boundary_plus_one(
    tmp_path: Path,
) -> None:
    files = {f"file_{number}.txt": "before\n" for number in range(4)}
    base, candidate = _trees(tmp_path, files)
    roomy = replace(POLICY, max_changed_lines=100)

    for number in range(3):
        write_text(candidate / f"file_{number}.txt", "after\n")
    at_boundary = ValidatorPipeline(roomy).run(base, candidate)
    assert at_boundary.stats.files_changed == 3
    assert at_boundary.passed

    write_text(candidate / "file_3.txt", "after\n")
    beyond_boundary = ValidatorPipeline(roomy).run(base, candidate)
    assert beyond_boundary.stats.files_changed == 4
    assert "max_files_changed" in [
        violation.rule_id for violation in beyond_boundary.violations
    ]


def test_changed_line_limit_accepts_boundary_and_rejects_boundary_plus_one(
    tmp_path: Path,
) -> None:
    base, candidate = _trees(tmp_path, {"data.txt": ""})

    write_text(candidate / "data.txt", "line\n" * 80)
    at_boundary = ValidatorPipeline(POLICY).run(base, candidate)
    assert at_boundary.stats.changed_lines == 80
    assert at_boundary.passed

    write_text(candidate / "data.txt", "line\n" * 81)
    beyond_boundary = ValidatorPipeline(POLICY).run(base, candidate)
    assert beyond_boundary.stats.changed_lines == 81
    assert "max_changed_lines" in [
        violation.rule_id for violation in beyond_boundary.violations
    ]


def test_new_file_is_rejected(tmp_path: Path) -> None:
    base, candidate = _trees(tmp_path, {"app.py": "value = 1\n"})
    write_text(candidate / "extra.py", "value = 2\n")

    assert "new_file" in _rule_ids(base, candidate)


def test_file_deletion_is_rejected(tmp_path: Path) -> None:
    base, candidate = _trees(tmp_path, {"app.py": "value = 1\n"})
    (candidate / "app.py").unlink()

    assert "file_deletion" in _rule_ids(base, candidate)


def test_binary_change_is_rejected(tmp_path: Path) -> None:
    base, candidate = _trees(tmp_path, {"asset.bin": "\x00before"})
    write_text(candidate / "asset.bin", "\x00after")

    assert "binary_file" in _rule_ids(base, candidate)


def test_pipeline_compares_trees_not_a_claimed_file_list(tmp_path: Path) -> None:
    base, candidate = _trees(tmp_path, {"app.py": "value = 1\n"})
    write_text(candidate / "tests/hidden_edit.py", "changed = True\n")

    result = ValidatorPipeline(POLICY).run(base, candidate)

    assert {violation.rule_id for violation in result.violations} >= {
        "new_file",
        "protected_path",
    }
