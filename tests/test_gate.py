from __future__ import annotations

from itertools import product

from backend.verification.gate import evaluate


GATE_NAMES = (
    "security",
    "regression",
    "post_scan",
    "policy",
    "integrity",
    "explain",
)


def test_exactly_one_of_all_64_gate_combinations_is_verified() -> None:
    verdicts = []
    for policy, security, regression, post_scan, integrity, explain in product(
        (False, True),
        repeat=6,
    ):
        verdict = evaluate(
            policy=policy,
            security=security,
            regression=regression,
            post_scan=post_scan,
            integrity=integrity,
            explain=explain,
        )
        verdicts.append(verdict)
        assert verdict.verified is all(
            (policy, security, regression, post_scan, integrity, explain)
        )

    assert sum(verdict.verified for verdict in verdicts) == 1


def test_failed_gates_and_first_failure_follow_the_documented_order() -> None:
    verdict = evaluate(
        policy=False,
        security=True,
        regression=False,
        post_scan=True,
        integrity=False,
        explain=True,
    )

    assert verdict.verified is False
    assert verdict.failed_gates == ("regression", "policy", "integrity")
    assert verdict.first_failure == "regression"
    assert verdict.reason == "regression gate failed"


def test_success_reason_is_explicit() -> None:
    verdict = evaluate(
        policy=True,
        security=True,
        regression=True,
        post_scan=True,
        integrity=True,
        explain=True,
    )

    assert verdict.verified is True
    assert verdict.failed_gates == ()
    assert verdict.first_failure is None
    assert verdict.reason == "all configured gates passed"
