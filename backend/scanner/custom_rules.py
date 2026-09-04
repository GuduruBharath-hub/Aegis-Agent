from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re

from backend.core.workspace import read_text


SQL_CONCAT_RULE = "AEGIS_SQL_CONCAT_EXECUTE"
_SQL_PREFIX = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE)
_EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "_aegis_runtime"}


@dataclass(frozen=True, slots=True)
class AstFinding:
    rule_id: str
    file_path: str
    line_start: int
    line_end: int
    symbol: str
    parameter: str
    message: str


def _is_string_construction(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    return False


def _static_text(node: ast.AST) -> str:
    return " ".join(
        value.value
        for value in ast.walk(node)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    )


class _SqlExecuteVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.function_stack: list[tuple[str, set[str]]] = []
        self.findings: list[AstFinding] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        parameters = {argument.arg for argument in node.args.args}
        parameters.update(argument.arg for argument in node.args.kwonlyargs)
        if node.args.vararg is not None:
            parameters.add(node.args.vararg.arg)
        if node.args.kwarg is not None:
            parameters.add(node.args.kwarg.arg)
        self.function_stack.append((node.name, parameters))
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:
        if not self.function_stack or not node.args:
            self.generic_visit(node)
            return
        is_execute = isinstance(node.func, ast.Attribute) and node.func.attr == "execute"
        query = node.args[0]
        if not is_execute or not _is_string_construction(query):
            self.generic_visit(node)
            return

        symbol, parameters = self.function_stack[-1]
        referenced_parameters = sorted(
            {
                child.id
                for child in ast.walk(query)
                if isinstance(child, ast.Name) and child.id in parameters
            }
        )
        if not referenced_parameters or _SQL_PREFIX.search(_static_text(query)) is None:
            self.generic_visit(node)
            return

        self.findings.append(
            AstFinding(
                rule_id=SQL_CONCAT_RULE,
                file_path=self.file_path,
                line_start=query.lineno,
                line_end=getattr(query, "end_lineno", query.lineno),
                symbol=symbol,
                parameter=referenced_parameters[0],
                message=(
                    "SQL passed to execute() concatenates caller-controlled parameter "
                    f"'{referenced_parameters[0]}'"
                ),
            )
        )
        self.generic_visit(node)


def scan_custom_rules(root: Path) -> tuple[AstFinding, ...]:
    workspace = root.resolve()
    findings: list[AstFinding] = []
    for path in sorted(workspace.rglob("*.py")):
        relative = path.relative_to(workspace)
        if any(part in _EXCLUDED_PARTS for part in relative.parts):
            continue
        try:
            source = read_text(path)
            findings.extend(scan_source(source, relative.as_posix()))
        except (SyntaxError, UnicodeDecodeError):
            continue
    return tuple(findings)


def scan_source(source: str, file_path: str) -> tuple[AstFinding, ...]:
    tree = ast.parse(source, filename=file_path)
    visitor = _SqlExecuteVisitor(file_path)
    visitor.visit(tree)
    return tuple(visitor.findings)
