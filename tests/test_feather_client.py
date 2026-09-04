from __future__ import annotations

import asyncio
import json

import httpx
from pydantic import SecretStr

from backend.agent.feather_client import FeatherPatchModel
from backend.core.config import FeatherSettings
from backend.core.models import Finding


FINDING = Finding(
    id="finding-1",
    scanner="aegis-ast",
    rule_id="AEGIS-SQL-001",
    category="SQL_INJECTION",
    cwe="CWE-89",
    severity="HIGH",
    confidence="HIGH",
    file_path="app/database.py",
    line_start=8,
    line_end=8,
    symbol="lookup",
    message="query concatenates caller input",
)


def test_feather_adapter_returns_schema_valid_patch_proposal() -> None:
    api_key = "feather-test-secret"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == (
            "https://api.featherless.ai/v1/chat/completions"
        )
        assert request.headers["Authorization"] == f"Bearer {api_key}"
        body = json.loads(request.content)
        assert body["model"] == "moonshotai/Kimi-K3"
        assert body["response_format"] == {"type": "json_object"}
        assert body["stream"] is False
        assert body["temperature"] == 0
        assert body["seed"] == 0
        prompt = json.loads(body["messages"][1]["content"])
        assert prompt["finding"]["id"] == FINDING.id
        assert prompt["repository_context"] == "source context"
        assert prompt["policy_summary"] == "policy summary"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Use a bound SQL parameter",
                                    "files": [
                                        {
                                            "path": "app/database.py",
                                            "new_content": "def lookup():\n    pass\n",
                                        }
                                    ],
                                }
                            )
                        }
                    }
                ]
            },
        )

    settings = FeatherSettings(
        FEATHER_API_KEY=SecretStr(api_key),
        FEATHER_BASE_URL="https://api.featherless.ai/v1",
        AEGIS_MODEL="moonshotai/Kimi-K3",
    )
    model = FeatherPatchModel(settings, transport=httpx.MockTransport(handler))

    proposal = asyncio.run(
        model.generate_patch(
            FINDING,
            context="source context",
            policy_summary="policy summary",
        )
    )

    assert proposal.summary == "Use a bound SQL parameter"
    assert proposal.files[0].path == "app/database.py"
    assert api_key not in repr(proposal)
