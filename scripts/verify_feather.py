from __future__ import annotations

import asyncio

from backend.agent.feather_client import FeatherPatchModel
from backend.core.config import FeatherSettings
from backend.core.models import Finding


SMOKE_FINDING = Finding(
    id="AEGIS-FEATHER-SMOKE",
    scanner="aegis-smoke",
    rule_id="AEGIS-SQL-001",
    category="SQL_INJECTION",
    cwe="CWE-89",
    severity="HIGH",
    confidence="HIGH",
    file_path="app/database.py",
    line_start=2,
    line_end=2,
    symbol="lookup",
    message="SQL query text includes caller-controlled input",
)

SMOKE_CONTEXT = """<untrusted_repository_content path="app/database.py">
def lookup(connection, term):
    return connection.execute("SELECT * FROM users WHERE name = '" + term + "'")
</untrusted_repository_content>
"""


async def main() -> None:
    settings = FeatherSettings()
    proposal = await FeatherPatchModel(settings).generate_patch(
        SMOKE_FINDING,
        context=SMOKE_CONTEXT,
        policy_summary=(
            "Change at most three existing Python files. Do not modify tests or "
            "dependencies. Return complete file contents, not a diff."
        ),
    )
    print(proposal.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
