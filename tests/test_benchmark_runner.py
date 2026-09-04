from scripts.run_benchmark import summary


def test_summary_counts_false_verification_only_on_refusal_cases() -> None:
    results = [
        {"expected_decision": "verified", "actual_decision": "verified", "correct": True},
        {"expected_decision": "escalated", "actual_decision": "escalated", "correct": True},
        {"expected_decision": "policy_rejected", "actual_decision": "verified", "correct": False},
    ]

    assert summary(results) == {
        "cases": 3,
        "correct": 2,
        "false_verifications": 1,
        "refusal_cases": 2,
    }
