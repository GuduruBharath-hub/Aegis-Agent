from __future__ import annotations

import ast
from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
from pathlib import Path

from backend.agent.injection_scan import InjectionFinding, scan
from backend.agent.redaction import redact
from backend.core.models import Finding
from backend.core.workspace import read_text
from backend.validator.protected_paths import PathEscapeError, normalize_relative_path


DEFAULT_DENY_GLOBS: tuple[str, ...] = (
    ".git/**",
    ".env",
    ".env.*",
    "**/*.pem",
    "**/*.key",
    "**/credentials.*",
    "**/secrets.*",
    "aegis_hidden_tests/**",
    "_aegis_runtime/**",
    "**/aegis_hidden_tests/**",
    "**/_aegis_runtime/**",
)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml"}
)


class ContextBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ContextDocument:
    path: str
    kind: str
    content: str
    complete: bool


@dataclass(frozen=True, slots=True)
class ContextPackage:
    rendered: str
    documents: tuple[ContextDocument, ...]
    bytes_used: int
    redactions: int
    injection_findings: tuple[InjectionFinding, ...]
    truncated: bool


class ContextBuilder:
    def __init__(
        self,
        *,
        max_bytes: int = 50_000,
        max_target_bytes: int = 20_000,
        deny_globs: tuple[str, ...] = DEFAULT_DENY_GLOBS,
    ) -> None:
        if max_bytes < 1 or max_target_bytes < 1:
            raise ValueError("context byte budgets must be positive")
        self.max_bytes = max_bytes
        self.max_target_bytes = min(max_target_bytes, max_bytes)
        self.deny_globs = deny_globs

    def build(self, root: Path, finding: Finding) -> ContextPackage:
        resolved_root = root.resolve()
        target_path = self._normalize_allowed(resolved_root, finding.file_path)
        source = read_text(resolved_root / Path(target_path))
        target_content, target_complete = self._target_context(source, finding)

        candidates: list[tuple[str, str, str, bool]] = [
            (target_path, "finding_source", target_content, target_complete)
        ]
        tests_root = resolved_root / "tests"
        if tests_root.is_dir():
            for path in sorted(tests_root.rglob("*.py")):
                relative = path.relative_to(resolved_root).as_posix()
                try:
                    normalized = self._normalize_allowed(resolved_root, relative)
                except ContextBuildError:
                    continue
                candidates.append(
                    (normalized, "public_test", read_text(resolved_root / normalized), True)
                )

        documents: list[ContextDocument] = []
        blocks: list[str] = []
        injections: list[InjectionFinding] = []
        redaction_count = 0
        truncated = not target_complete

        for path, kind, content, complete in candidates:
            redaction = redact(content)
            block = self._render_block(path, kind, redaction.text, complete)
            projected = "\n\n".join([*blocks, block])
            if len(projected.encode("utf-8")) > self.max_bytes:
                if kind == "finding_source":
                    raise ContextBuildError("finding context exceeds the byte budget")
                truncated = True
                continue
            document = ContextDocument(path, kind, redaction.text, complete)
            documents.append(document)
            blocks.append(block)
            redaction_count += redaction.count
            injections.extend(scan(path, redaction.text))

        rendered = "\n\n".join(blocks)
        return ContextPackage(
            rendered=rendered,
            documents=tuple(documents),
            bytes_used=len(rendered.encode("utf-8")),
            redactions=redaction_count,
            injection_findings=tuple(injections),
            truncated=truncated,
        )

    def _normalize_allowed(self, root: Path, untrusted_path: str) -> str:
        try:
            normalized = normalize_relative_path(root, untrusted_path)
        except PathEscapeError as exc:
            raise ContextBuildError(str(exc)) from exc
        if self._denied(normalized):
            raise ContextBuildError(f"context path is denied: {normalized}")
        if Path(normalized).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ContextBuildError(f"context extension is not allowed: {normalized}")
        resolved = root / Path(normalized)
        if not resolved.is_file():
            raise ContextBuildError(f"context file does not exist: {normalized}")
        return normalized

    def _denied(self, path: str) -> bool:
        return any(_matches(path, pattern) for pattern in self.deny_globs)

    def _target_context(self, source: str, finding: Finding) -> tuple[str, bool]:
        if len(source.encode("utf-8")) <= self.max_target_bytes:
            return source, True

        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise ContextBuildError("finding source is not valid Python") from exc
        lines = source.splitlines(keepends=True)
        nodes: list[ast.AST] = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        containing = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.lineno <= finding.line_start <= (node.end_lineno or node.lineno)
        ]
        if not containing:
            raise ContextBuildError("no enclosing function contains the finding line")
        nodes.append(
            min(
                containing,
                key=lambda node: (node.end_lineno or node.lineno) - node.lineno,
            )
        )
        ranges = sorted(
            (node.lineno, node.end_lineno or node.lineno)
            for node in nodes
        )
        excerpts = [
            "".join(lines[start - 1 : end]).rstrip("\n")
            for start, end in ranges
        ]
        focused = "\n\n# ... unrelated module content omitted ...\n\n".join(excerpts)
        if len(focused.encode("utf-8")) > self.max_target_bytes:
            raise ContextBuildError("focused finding context exceeds the byte budget")
        return focused + "\n", False

    @staticmethod
    def _render_block(path: str, kind: str, content: str, complete: bool) -> str:
        completeness = "complete" if complete else "focused_excerpt"
        return (
            f"<untrusted_repository_content path={json.dumps(path)} "
            f'kind="{kind}" coverage="{completeness}">\n{content}\n'
            "</untrusted_repository_content>"
        )


def _matches(path: str, pattern: str) -> bool:
    if fnmatchcase(path, pattern):
        return True
    return pattern.startswith("**/") and fnmatchcase(path, pattern[3:])
