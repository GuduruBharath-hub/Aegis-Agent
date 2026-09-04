from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.agent.llm_client import PatchProposal
from backend.core.config import FeatherSettings
from backend.core.models import FailureEvidence, Finding


class FeatherProviderError(RuntimeError):
    pass


class FeatherResponseError(FeatherProviderError):
    pass


class _Message(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str | None = None


class _Choice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: _Message


class _ChatCompletion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    choices: tuple[_Choice, ...] = Field(min_length=1)


class FeatherPatchModel:
    def __init__(
        self,
        settings: FeatherSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.name = settings.model
        self._transport = transport
        self._concurrency = asyncio.Semaphore(settings.concurrency)

    async def generate_patch(
        self,
        finding: Finding,
        context: str = "",
        policy_summary: str = "",
        failure_evidence: FailureEvidence | None = None,
    ) -> PatchProposal:
        payload = self._request_payload(
            finding,
            context,
            policy_summary,
            failure_evidence,
        )
        headers = {
            "Authorization": (
                f"Bearer {self.settings.api_key.get_secret_value()}"
            ),
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/GuduruBharath-hub/Aegis-Agent",
            "X-Title": "AegisAgent",
        }
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"

        try:
            async with self._concurrency:
                async with httpx.AsyncClient(
                    timeout=self.settings.timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FeatherProviderError(
                f"Featherless returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise FeatherProviderError("Featherless request failed") from exc

        try:
            completion = _ChatCompletion.model_validate(response.json())
            content = completion.choices[0].message.content
            if content is None:
                raise ValueError("response message has no content")
            return PatchProposal.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise FeatherResponseError(
                "Featherless returned an invalid PatchProposal"
            ) from exc

    def _request_payload(
        self,
        finding: Finding,
        context: str,
        policy_summary: str,
        failure_evidence: FailureEvidence | None,
    ) -> dict[str, Any]:
        request = {
            "finding": asdict(finding),
            "repository_context": context,
            "policy_summary": policy_summary,
            "failure_evidence": (
                asdict(failure_evidence) if failure_evidence is not None else None
            ),
            "output_schema": PatchProposal.model_json_schema(),
        }
        return {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Propose a minimal security patch. Return only one JSON "
                        "object that satisfies the supplied output_schema."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(request, sort_keys=True),
                },
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "seed": 0,
            "stream": False,
        }
