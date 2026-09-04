from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from backend.core.models import PolicyResult, PolicyViolation
from backend.core.workspace import read_text
from backend.validator.ast_rules import find_ast_violations
from backend.validator.diff_policy import (
    compare_trees,
    diff_stats,
    find_diff_violations,
)
from backend.validator.protected_paths import find_protected_path_violations
from backend.validator.syntax import find_syntax_violations


@dataclass(frozen=True, slots=True)
class ValidatorPolicy:
    max_files_changed: int
    max_changed_lines: int
    allow_new_files: bool
    allow_file_deletion: bool
    protected_paths: tuple[str, ...]
    denied_symbols: tuple[str, ...]
    denied_imports: tuple[str, ...]

    @classmethod
    def from_file(cls, path: Path) -> ValidatorPolicy:
        raw: dict[str, Any] = json.loads(read_text(path))
        return cls(
            max_files_changed=int(raw["max_files_changed"]),
            max_changed_lines=int(raw["max_changed_lines"]),
            allow_new_files=bool(raw["allow_new_files"]),
            allow_file_deletion=bool(raw["allow_file_deletion"]),
            protected_paths=tuple(raw["protected_paths"]),
            denied_symbols=tuple(raw["denied_symbols"]),
            denied_imports=tuple(raw["denied_imports"]),
        )


class ValidatorPipeline:
    def __init__(self, policy: ValidatorPolicy) -> None:
        self.policy = policy

    def run(self, base: Path, candidate: Path) -> PolicyResult:
        changes = compare_trees(base, candidate)
        violations: list[PolicyViolation] = []

        violations.extend(find_syntax_violations(candidate, changes))
        violations.extend(
            find_protected_path_violations(
                candidate,
                (change.path for change in changes),
                self.policy.protected_paths,
            )
        )
        violations.extend(
            find_diff_violations(
                changes,
                max_files_changed=self.policy.max_files_changed,
                max_changed_lines=self.policy.max_changed_lines,
                allow_new_files=self.policy.allow_new_files,
                allow_file_deletion=self.policy.allow_file_deletion,
            )
        )
        violations.extend(
            find_ast_violations(
                candidate,
                changes,
                denied_symbols=self.policy.denied_symbols,
                denied_imports=self.policy.denied_imports,
            )
        )
        return PolicyResult(tuple(violations), diff_stats(changes))
