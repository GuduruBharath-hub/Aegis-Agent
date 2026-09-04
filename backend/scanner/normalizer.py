from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath

from backend.core.models import Finding
from backend.scanner.bandit_runner import BanditScan, run_bandit
from backend.scanner.custom_rules import (
    COMMAND_SHELL_RULE,
    AstFinding,
    scan_custom_rules,
)


def _stable_id(rule_id: str, file_path: str, symbol: str) -> str:
    identity = f"{rule_id}\0{file_path}\0{symbol}".encode("utf-8")
    return f"AEGIS-{hashlib.sha256(identity).hexdigest()[:12].upper()}"


def _normalise_bandit_path(value: object) -> str:
    path = str(value).replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return PurePosixPath(path).as_posix()


def _bandit_confirms(custom: AstFinding, result: dict[str, object]) -> bool:
    expected_bandit_rule = "B602" if custom.rule_id == COMMAND_SHELL_RULE else "B608"
    if result.get("test_id") != expected_bandit_rule:
        return False
    if _normalise_bandit_path(result.get("filename")) != custom.file_path:
        return False
    bandit_lines = result.get("line_range")
    if not isinstance(bandit_lines, list) or not all(
        isinstance(line, int) for line in bandit_lines
    ):
        line_number = result.get("line_number")
        bandit_lines = [line_number] if isinstance(line_number, int) else []
    return any(custom.line_start <= line <= custom.line_end for line in bandit_lines)


def normalize(
    bandit: BanditScan,
    custom_findings: tuple[AstFinding, ...],
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for custom in custom_findings:
        confirmed = any(_bandit_confirms(custom, result) for result in bandit.results)
        scanner = "aegis-ast+bandit" if confirmed else "aegis-ast"
        command_injection = custom.rule_id == COMMAND_SHELL_RULE
        findings.append(
            Finding(
                id=_stable_id(custom.rule_id, custom.file_path, custom.symbol),
                scanner=scanner,
                rule_id=custom.rule_id,
                category="COMMAND_INJECTION" if command_injection else "SQL_INJECTION",
                cwe="CWE-78" if command_injection else "CWE-89",
                severity="HIGH",
                confidence="HIGH",
                file_path=custom.file_path,
                line_start=custom.line_start,
                line_end=custom.line_end,
                symbol=custom.symbol,
                message=custom.message,
            )
        )
    return tuple(findings)


def scan_repository(root: Path) -> tuple[Finding, ...]:
    workspace = root.resolve()
    return normalize(run_bandit(workspace), scan_custom_rules(workspace))
