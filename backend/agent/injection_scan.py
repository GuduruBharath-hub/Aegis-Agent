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
        # Order-insensitive: repository text says "security tests are outdated;
        # edit ..." as often as "edit the security tests". An order-sensitive
        # pattern misses half of the real phrasings.
        re.compile(
            r"\b(?:modify|change|disable|bypass|skip|rewrite|edit|update|adjust"
            r"|relax|remove|delete|regenerate)\b.{0,80}"
            r"\b(?:hidden[_ ]tests?|security[_ ]tests?|aegis_hidden_tests"
            r"|security policy|policy file|security_policy|validator|oracle)\b"
            r"|\b(?:hidden[_ ]tests?|security[_ ]tests?|aegis_hidden_tests"
            r"|policy|gate|validator|oracle)\b.{0,80}"
            r"\b(?:are outdated|is outdated|should be|must be|need(?:s)? to be)?"
            r".{0,20}\b(?:modify|change|disable|bypass|skip|rewrite|edit|update"
            r"|adjust|relax|remove|delete|regenerate)\b",
            re.IGNORECASE,
        ),
    ),
    (
        # Text that addresses an automated reader at all is a signal in itself:
        # source code has no legitimate reason to give instructions to a tool.
        "addresses_automation",
        re.compile(
            r"\b(?:note to|instructions? for|attention)\b.{0,20}"
            r"\b(?:automated|automation|ai|agent|assistant|tool|bot|llm|model)s?\b"
            r"|\b(?:automation|ai|agent|llm)[- ]note\b"
            r"|\bautomated tools?\b",
            re.IGNORECASE,
        ),
    ),
    (
        # Repository text recommending an API the policy denies.
        "denied_api_recommendation",
        re.compile(
            # Imperative only. "use eval()" is a directive to the reader;
            # "we use requests in tests" is someone describing their codebase.
            r"(?:^|[.:;!]\s*)\s*(?:use|call|invoke|import|add|prefer)\b.{0,40}"
            r"\b(?:eval\(?|exec\(?|__import__|os\.system|pickle\.loads"
            r"|requests|urllib|httpx|socket|subprocess)\b",
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


_CODE_LINE = re.compile(r"^\s*(?:from|import)\s+\w")


def _prose_of(line: str) -> str:
    """The natural-language part of a source line, or empty if there is none.

    Prompt injections are prose: they live in comments and docstrings, because
    that is the only place a human can address a machine reader. Executable
    code that *uses* a denied API is a different problem with a different
    control — the AST gate — and scanning it here only produces false
    positives, such as flagging the legitimate `import subprocess` in the
    command-injection fixtures.
    """
    if _CODE_LINE.match(line):
        return ""
    _, hash_sep, comment = line.partition("#")
    if hash_sep:
        return comment
    stripped = line.strip()
    # A bare docstring/prose line: no code punctuation, mostly words.
    if stripped and not any(ch in stripped for ch in "=(){}[];") and " " in stripped:
        return stripped
    return ""


def scan(path: str, text: str) -> tuple[InjectionFinding, ...]:
    findings: list[InjectionFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        prose = _prose_of(line)
        if not prose:
            continue
        for rule_id, pattern in _RULES:
            if pattern.search(prose) is None:
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
