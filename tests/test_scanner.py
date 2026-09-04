from pathlib import Path

import pytest

from backend.scanner.custom_rules import scan_source
from backend.scanner.normalizer import scan_repository


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_sql_retry_emits_one_normalized_search_finding() -> None:
    findings = scan_repository(REPOSITORY_ROOT / "benchmarks" / "sql_retry")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.cwe == "CWE-89"
    assert finding.category == "SQL_INJECTION"
    assert finding.severity == "HIGH"
    assert finding.confidence == "HIGH"
    assert finding.file_path == "app/database.py"
    assert finding.symbol == "search_users"
    assert finding.scanner == "aegis-ast+bandit"
    assert finding.id.startswith("AEGIS-")


@pytest.mark.parametrize(
    "query_expression",
    [
        '"SELECT * FROM users WHERE id = " + uid',
        'f"SELECT * FROM users WHERE id = {uid}"',
        '"SELECT * FROM users WHERE id = %s" % uid',
    ],
)
def test_custom_rule_detects_supported_string_constructions(
    query_expression: str,
) -> None:
    source = (
        "def find_user(cursor, uid):\n"
        f"    return cursor.execute({query_expression}).fetchone()\n"
    )

    findings = scan_source(source, "app/users.py")

    assert len(findings) == 1
    assert findings[0].symbol == "find_user"
    assert findings[0].parameter == "uid"


def test_custom_rule_ignores_bound_parameters() -> None:
    source = (
        "def find_user(cursor, uid):\n"
        '    return cursor.execute("SELECT * FROM users WHERE id = ?", (uid,))\n'
    )

    assert scan_source(source, "app/users.py") == ()
