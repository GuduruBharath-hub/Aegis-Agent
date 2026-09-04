from __future__ import annotations

import ast
from pathlib import Path

from backend.core.models import PolicyViolation
from backend.core.workspace import read_text
from backend.validator.diff_policy import FileChange


def find_ast_violations(
    candidate: Path,
    changes: tuple[FileChange, ...],
    *,
    denied_symbols: tuple[str, ...],
    denied_imports: tuple[str, ...],
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
            tree = ast.parse(read_text(candidate / change.path), filename=change.path)
        except SyntaxError:
            # Syntax owns this failure so the pipeline reports each cause once.
            continue
        visitor = _DenylistVisitor(
            path=change.path,
            denied_symbols=frozenset(denied_symbols),
            denied_imports=frozenset(denied_imports),
        )
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return tuple(violations)


class _DenylistVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        path: str,
        denied_symbols: frozenset[str],
        denied_imports: frozenset[str],
    ) -> None:
        self.path = path
        self.denied_symbols = denied_symbols
        self.denied_imports = denied_imports
        self.aliases: dict[str, str] = {}
        self.violations: list[PolicyViolation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self.aliases[local_name] = alias.name
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        self._check_import(node.module, node.lineno)
        for alias in node.names:
            local_name = alias.asname or alias.name
            self.aliases[local_name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        symbol = _qualified_name(node.func)
        if symbol is not None:
            root, separator, remainder = symbol.partition(".")
            if root in self.aliases:
                symbol = self.aliases[root] + (separator + remainder if separator else "")
            if symbol in self.denied_symbols:
                self.violations.append(
                    PolicyViolation(
                        "denied_symbol",
                        f"call to denied symbol: {symbol}",
                        path=self.path,
                        line=node.lineno,
                    )
                )
        self.generic_visit(node)

    def _check_import(self, module: str, line: int) -> None:
        root = module.split(".")[0]
        if root in self.denied_imports:
            self.violations.append(
                PolicyViolation(
                    "denied_import",
                    f"import of denied module: {module}",
                    path=self.path,
                    line=line,
                )
            )


def _qualified_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _qualified_name(node.value)
        if owner is not None:
            return f"{owner}.{node.attr}"
    return None
