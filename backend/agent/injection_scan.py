from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class InjectionFinding:
    path: str
    line: int
    rule_id: str
    excerpt: str


_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore|disregard|override)\b.{0,50}\b(?:previous|prior|system)\b"
            r".{0,30}\b(?:instruction|prompt|rule)s?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_impersonation",
        re.compile(
            r"\b(?:you are|act as)\b.{0,30}\b(?:assistant|system|chatgpt|model)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "control_plane_tampering",
        re.compile(
            r"\b(?:modify|change|disable|bypass|skip|rewrite)\b.{0,60}"
            r"\b(?:hidden tests?|security tests?|policy|gate|validator)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "secret_exfiltration",
        re.compile(
            r"\b(?:reveal|print|return|send|exfiltrate)\b.{0,50}"
            r"\b(?:secret|token|api[_ -]?key|credential|password)s?\b",
            re.IGNORECASE,
        ),
    ),
)


def scan(path: str, text: str) -> tuple[InjectionFinding, ...]:
    findings: list[InjectionFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern in _RULES:
            if pattern.search(line) is None:
                continue
            findings.append(
                InjectionFinding(
                    path=path,
                    line=line_number,
                    rule_id=rule_id,
                    excerpt=line.strip()[:200],
                )
            )
    return tuple(findings)
