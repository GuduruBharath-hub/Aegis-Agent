from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Verdict:
    verified: bool
    decision: Literal["verified", "rejected"]
    failed_gates: tuple[str, ...]
    first_failure: str | None
    reason: str


def evaluate(
    *,
    policy: bool,
    security: bool,
    regression: bool,
    post_scan: bool,
    integrity: bool,
    explain: bool,
) -> Verdict:
    gates = (
        ("security", security),
        ("regression", regression),
        ("post_scan", post_scan),
        ("policy", policy),
        ("integrity", integrity),
        ("explain", explain),
    )
    failed = tuple(name for name, passed in gates if not passed)
    first_failure = failed[0] if failed else None
    reason = (
        f"{first_failure} gate failed"
        if first_failure is not None
        else "all configured gates passed"
    )
    return Verdict(
        verified=not failed,
        decision="rejected" if failed else "verified",
        failed_gates=failed,
        first_failure=first_failure,
        reason=reason,
    )
