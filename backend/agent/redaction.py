from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class RedactionResult:
    text: str
    count: int
    categories: tuple[str, ...]


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "pem_private_key",
        re.compile(
            r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----.*?"
            r"-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
)

_ASSIGNED_SECRET = re.compile(
    r"(?im)(?P<prefix>\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"secret|password)\b\s*[:=]\s*[\"']?)(?P<value>[^\s\"']{8,})"
    r"(?P<suffix>[\"']?)"
)


def redact(text: str) -> RedactionResult:
    categories: list[str] = []
    count = 0

    def replace_assignment(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        categories.append("assigned_secret")
        return (
            f"{match.group('prefix')}<REDACTED:assigned_secret>"
            f"{match.group('suffix')}"
        )

    redacted = _ASSIGNED_SECRET.sub(replace_assignment, text)
    for category, pattern in _SECRET_PATTERNS:
        def replace_known_secret(
            match: re.Match[str],
            *,
            matched_category: str = category,
        ) -> str:
            nonlocal count
            count += 1
            categories.append(matched_category)
            line_padding = "\n" * match.group(0).count("\n")
            return f"<REDACTED:{matched_category}>{line_padding}"

        redacted = pattern.sub(replace_known_secret, redacted)
    return RedactionResult(redacted, count, tuple(categories))
