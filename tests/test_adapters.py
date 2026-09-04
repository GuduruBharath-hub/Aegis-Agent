from backend.adapters import select_adapter
from backend.core.models import Finding


def _finding(category: str) -> Finding:
    return Finding(
        "finding",
        "scanner",
        "rule",
        category,
        "CWE",
        "HIGH",
        "HIGH",
        "app.py",
        1,
        1,
        "function",
        "message",
    )


def test_registry_selects_both_supported_adapters() -> None:
    assert select_adapter(_finding("SQL_INJECTION")) == "sql_injection"
    assert select_adapter(_finding("COMMAND_INJECTION")) == "command_injection"
