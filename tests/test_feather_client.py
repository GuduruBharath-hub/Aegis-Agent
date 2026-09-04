from __future__ import annotations

import asyncio
import json

import httpx
from pydantic import SecretStr

from backend.agent.feather_client import FeatherPatchModel, extract_json_object
from backend.agent.llm_client import ModelTechnicalError
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
        prompt = body["messages"][1]["content"]
        assert FINDING.id in prompt
        assert "source context" in prompt
        assert "policy summary" in prompt
        assert "ORIGINAL REPOSITORY CONTEXT" in prompt
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


def test_extract_json_tolerates_fences_and_surrounding_prose() -> None:
    assert extract_json_object('Result:\n```json\n{"ok": true}\n```\nDone.') == {
        "ok": True
    }


def test_malformed_output_is_reported_then_repaired() -> None:
    requests: list[dict[str, object]] = []
    errors: list[ModelTechnicalError] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            content = '{"summary": "files are missing"}'
        else:
            repair = json.loads(body["messages"][-1]["content"])
            assert repair["repair"] == "Return only a corrected JSON object."
            content = json.dumps(
                {
                    "summary": "Use a bound parameter",
                    "files": [
                        {
                            "path": "app/database.py",
                            "new_content": "fixed = True\n",
                        }
                    ],
                }
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
        )

    async def report(error: ModelTechnicalError) -> None:
        errors.append(error)

    settings = FeatherSettings(
        FEATHER_API_KEY=SecretStr("test-key"),
        AEGIS_LLM_TRANSPORT_RETRIES=2,
    )
    model = FeatherPatchModel(settings, transport=httpx.MockTransport(handler))

    proposal = asyncio.run(
        model.generate_patch(FINDING, report_technical_error=report)
    )

    assert proposal.files[0].new_content == "fixed = True\n"
    assert len(requests) == 2
    assert [error.code for error in errors] == ["malformed_model_output"]
    assert errors[0].request_number == 1
    assert errors[0].max_requests == 3


def test_provider_5xx_retries_with_bounded_backoff() -> None:
    request_count = 0
    delays: list[float] = []
    errors: list[ModelTechnicalError] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Recovered",
                                    "files": [
                                        {
                                            "path": "app/database.py",
                                            "new_content": "fixed = True\n",
                                        }
                                    ],
                                }
                            )
                        }
                    }
                ]
            },
        )

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def report(error: ModelTechnicalError) -> None:
        errors.append(error)

    settings = FeatherSettings(
        FEATHER_API_KEY=SecretStr("test-key"),
        AEGIS_LLM_TRANSPORT_RETRIES=2,
    )
    model = FeatherPatchModel(
        settings,
        transport=httpx.MockTransport(handler),
        sleep=sleep,
    )

    proposal = asyncio.run(
        model.generate_patch(FINDING, report_technical_error=report)
    )

    assert proposal.summary == "Recovered"
    assert request_count == 3
    assert delays == [1, 2]
    assert [error.code for error in errors] == [
        "provider_http_503",
        "provider_http_503",
    ]
