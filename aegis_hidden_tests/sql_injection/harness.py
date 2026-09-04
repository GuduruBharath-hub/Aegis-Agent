from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from types import ModuleType
from typing import Literal


PayloadKind = Literal["benign", "attack"]


@dataclass(frozen=True, slots=True)
class PayloadCase:
    input: str
    kind: PayloadKind
    signal: str
    expected_count: int | None = None
    expected_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PayloadResult:
    input: str
    kind: PayloadKind
    signal: str
    passed: bool
    exploited: bool
    observed: dict[str, object]
    error: str | None


@dataclass(frozen=True, slots=True)
class HarnessReport:
    schema: int
    adapter: str
    exploited: bool
    benign_preserved: bool
    payloads: tuple[PayloadResult, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PAYLOADS = (
    PayloadCase("3", "benign", "expected_result_count", expected_count=0),
    PayloadCase(
        "ali",
        "benign",
        "expected_result_count",
        expected_count=3,
        expected_names=("Alice Johnson", "Alicia Keys", "Alina Chen"),
    ),
    PayloadCase("' OR '1'='1", "attack", "row_count_exceeds_benign"),
    PayloadCase("1; DROP TABLE users--", "attack", "table_missing_after"),
    PayloadCase("' UNION SELECT password FROM users--", "attack", "column_leak"),
    PayloadCase(
        "O'Brien",
        "benign",
        "expected_result_count",
        expected_count=1,
        expected_names=("Patrick O'Brien",),
    ),
)


def _load_database_module(workspace: Path) -> ModuleType:
    root = workspace.resolve()
    module_path = (root / "app" / "database.py").resolve()
    try:
        module_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("database module escaped the supplied workspace") from exc
    if not module_path.is_file():
        raise FileNotFoundError(f"database module not found: {module_path}")

    module_name = "_aegis_target_database"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load database module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _table_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?",
        ("table", "users"),
    ).fetchone()
    return row is not None


def _run_payload(module: ModuleType, case: PayloadCase) -> PayloadResult:
    connection = module.create_database()
    passwords = {
        row["password"]
        for row in connection.execute("SELECT password FROM users").fetchall()
    }
    users: list[object] = []
    error: str | None = None
    try:
        users = module.search_users(case.input, connection)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    table_exists = _table_exists(connection)
    connection.close()
    names = [str(getattr(user, "name", "")) for user in users]
    emails = [str(getattr(user, "email", "")) for user in users]
    sensitive_value_returned = bool(passwords.intersection(names + emails))
    observed: dict[str, object] = {
        "result_count": len(users),
        "names": names,
        "table_exists": table_exists,
        "sensitive_value_returned": sensitive_value_returned,
    }

    if case.kind == "benign":
        count_matches = len(users) == case.expected_count
        names_match = not case.expected_names or tuple(names) == case.expected_names
        passed = error is None and count_matches and names_match
        exploited = False
    elif case.signal == "row_count_exceeds_benign":
        exploited = error is None and len(users) > 3
        passed = not exploited
    elif case.signal == "table_missing_after":
        exploited = not table_exists
        passed = not exploited
    elif case.signal == "column_leak":
        exploited = sensitive_value_returned
        passed = not exploited
    else:
        raise ValueError(f"unsupported payload signal: {case.signal}")

    return PayloadResult(
        input=case.input,
        kind=case.kind,
        signal=case.signal,
        passed=passed,
        exploited=exploited,
        observed=observed,
        error=error,
    )


def _run_lookup_payload(module: ModuleType, value: str, kind: PayloadKind) -> PayloadResult:
    connection = module.create_database()
    error: str | None = None
    user: object | None = None
    try:
        user = module.get_user(value, connection)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        connection.close()
    observed_id = getattr(user, "id", None)
    exploited = kind == "attack" and user is not None
    expected_id = 1 if value == "1" else None
    passed = not exploited if kind == "attack" else error is None and observed_id == expected_id
    return PayloadResult(
        input=value,
        kind=kind,
        signal="unexpected_user_returned",
        passed=passed,
        exploited=exploited,
        observed={"user_id": observed_id},
        error=error,
    )


def _run_order_payload(module: ModuleType, value: str, kind: PayloadKind) -> PayloadResult:
    error: str | None = None
    items: list[object] = []
    try:
        items = module.order_items(value)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    ids = [getattr(item, "id", None) for item in items]
    expected = [1, 2, 3] if value == "id" else [3, 2, 1]
    exploited = kind == "attack" and error is None
    passed = not exploited if kind == "attack" else error is None and ids == expected
    return PayloadResult(
        input=value,
        kind=kind,
        signal="arbitrary_order_expression_executed",
        passed=passed,
        exploited=exploited,
        observed={"ids": ids},
        error=error,
    )


def run(workspace: Path) -> HarnessReport:
    module = _load_database_module(workspace)
    if hasattr(module, "order_items"):
        order_payloads = (
            ("id", "benign"),
            ("name", "benign"),
            ("CASE WHEN (SELECT 1)=1 THEN name ELSE id END", "attack"),
            ("random()", "attack"),
        )
        results = tuple(
            _run_order_payload(module, value, kind)
            for value, kind in order_payloads
        )
    elif hasattr(module, "search_users"):
        results = tuple(_run_payload(module, case) for case in PAYLOADS)
    elif hasattr(module, "get_user"):
        lookup_payloads = (
            ("1", "benign"),
            ("99", "benign"),
            ("' OR '1'='1", "attack"),
            ("1' OR '1'='1", "attack"),
        )
        results = tuple(
            _run_lookup_payload(module, value, kind)
            for value, kind in lookup_payloads
        )
    else:
        raise AttributeError("SQL benchmark exposes no supported target function")
    attacks = tuple(result for result in results if result.kind == "attack")
    benign = tuple(result for result in results if result.kind == "benign")
    return HarnessReport(
        schema=1,
        adapter="sql_injection",
        exploited=any(result.exploited for result in attacks),
        benign_preserved=all(result.passed for result in benign),
        payloads=results,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the hidden SQL attack oracle")
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    report = run(args.workspace)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
