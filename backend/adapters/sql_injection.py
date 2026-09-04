from __future__ import annotations

from typing import Literal

from backend.core.models import Finding


class SqlInjectionAdapter:
    name: Literal["sql_injection"] = "sql_injection"

    def can_handle(self, finding: Finding) -> bool:
        return finding.category == "SQL_INJECTION"
