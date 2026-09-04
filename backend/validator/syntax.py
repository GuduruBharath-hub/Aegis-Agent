from __future__ import annotations

import ast
from pathlib import Path

from backend.core.models import PolicyViolation
from backend.core.workspace import read_text
from backend.validator.diff_policy import FileChange


def find_syntax_violations(
    candidate: Path,
    changes: tuple[FileChange, ...],
) -> tuple[PolicyViolation, ...]:
    violations: list[PolicyViolation] = []
    for change in changes:
        if (
            not change.path.endswith(".py")
            or change.kind == "deleted"
            or change.binary
            or change.symbolic_link
            or change.path_escape
        ):
            continue
        try:
            ast.parse(read_text(candidate / change.path), filename=change.path)
        except SyntaxError as exc:
            violations.append(
                PolicyViolation(
                    "syntax_error",
                    exc.msg,
                    path=change.path,
                    line=exc.lineno,
                )
            )
    return tuple(violations)
