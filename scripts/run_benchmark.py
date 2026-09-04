from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from time import monotonic, sleep
from typing import Any, Protocol

import httpx


class BenchmarkApi(Protocol):
    def get(self, url: str) -> Any: ...

    def post(self, url: str, *, json: dict[str, str]) -> Any: ...


def run_suite(
    client: BenchmarkApi,
    case_ids: Sequence[str],
    *,
    poll_seconds: float,
    timeout_seconds: float,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for case_id in case_ids:
        started = client.post(
            "/api/benchmarks/run",
            json={"scenario_id": case_id},
        )
        started.raise_for_status()
        run = started.json()
        deadline = monotonic() + timeout_seconds
        while run["status"] != "completed" and monotonic() < deadline:
            sleep(poll_seconds)
            response = client.get(f"/api/benchmarks/runs/{run['id']}")
            response.raise_for_status()
            run = response.json()
        if run["status"] != "completed":
            raise TimeoutError(f"benchmark case timed out: {case_id}")
        results.append(run)
        print(
            f"{case_id}: expected={run['expected_decision']} "
            f"actual={run['actual_decision']} correct={run['correct']}"
        )
    return results


def summary(results: Sequence[dict[str, object]]) -> dict[str, int]:
    refusals = [run for run in results if run["expected_decision"] != "verified"]
    return {
        "cases": len(results),
        "correct": sum(run.get("correct") is True for run in results),
        "false_verifications": sum(
            run.get("actual_decision") == "verified" for run in refusals
        ),
        "refusal_cases": len(refusals),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AegisAgent benchmark cases")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    args = parser.parse_args()
    if args.poll_seconds <= 0 or args.timeout_seconds <= 0:
        parser.error("poll and timeout values must be positive")

    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=30.0) as client:
        scenarios = client.get("/api/benchmarks/scenarios")
        scenarios.raise_for_status()
        available = [item["id"] for item in scenarios.json()]
        case_ids = args.cases or available
        unknown = sorted(set(case_ids) - set(available))
        if unknown:
            parser.error(f"unknown benchmark cases: {', '.join(unknown)}")
        results = run_suite(
            client,
            case_ids,
            poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds,
        )

    metrics = summary(results)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if metrics["correct"] == metrics["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
