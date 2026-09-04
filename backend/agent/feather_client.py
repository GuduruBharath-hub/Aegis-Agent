from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import asdict
import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.agent.llm_client import (
    ModelTechnicalError,
    PatchModelError,
    PatchProposal,
    TechnicalErrorReporter,
)
from backend.core.config import FeatherSettings
from backend.core.models import FailureEvidence, Finding


class FeatherProviderError(PatchModelError):
    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class FeatherResponseError(PatchModelError):
    def __init__(self, message: str, *, raw: str, detail: str) -> None:
        super().__init__(message)
        self.raw = raw
        self.detail = detail


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
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings
        self.name = settings.model
        self._transport = transport
        self._concurrency = asyncio.Semaphore(settings.concurrency)
        self._sleep = sleep

    async def generate_patch(
        self,
        finding: Finding,
        context: str = "",
        policy_summary: str = "",
        failure_evidence: FailureEvidence | None = None,
        report_technical_error: TechnicalErrorReporter | None = None,
    ) -> PatchProposal:
        payload = self._request_payload(
            finding,
            context,
            policy_summary,
            failure_evidence,
        )
        max_requests = self.settings.transport_retries + 1

        for request_number in range(1, max_requests + 1):
            try:
                raw = await self._complete(payload)
                return self._parse_proposal(raw)
            except FeatherProviderError as exc:
                await self._report(
                    report_technical_error,
                    ModelTechnicalError(
                        component="featherless",
                        code=exc.code,
                        message="Featherless request failed",
                        request_number=request_number,
                        max_requests=max_requests,
                    ),
                )
                if not exc.retryable or request_number == max_requests:
                    raise
                await self._sleep(self._backoff_seconds(request_number))
                continue
            except FeatherResponseError as exc:
                await self._report(
                    report_technical_error,
                    ModelTechnicalError(
                        component="featherless",
                        code="malformed_model_output",
                        message="Model response did not satisfy PatchProposal",
                        request_number=request_number,
                        max_requests=max_requests,
                    ),
                )
                if request_number == max_requests:
                    raise
                payload = self._repair_payload(payload, exc)

        raise AssertionError("bounded Featherless request loop did not terminate")

    async def _complete(self, payload: dict[str, Any]) -> str:
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
            status = exc.response.status_code
            raise FeatherProviderError(
                f"Featherless returned HTTP {status}",
                code=f"provider_http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except httpx.HTTPError as exc:
            raise FeatherProviderError(
                "Featherless request failed",
                code="provider_transport_error",
                retryable=True,
            ) from exc

        try:
            completion = _ChatCompletion.model_validate(response.json())
            content = completion.choices[0].message.content
            if content is None:
                raise ValueError("response message has no content")
            return content
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise FeatherResponseError(
                "Featherless returned an invalid completion envelope",
                raw="",
                detail=str(exc),
            ) from exc

    @staticmethod
    def _parse_proposal(raw: str) -> PatchProposal:
        try:
            candidate = extract_json_object(raw)
            return PatchProposal.model_validate(candidate)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            detail = (
                json.dumps(exc.errors(include_url=False), default=str)
                if isinstance(exc, ValidationError)
                else str(exc)
            )
            raise FeatherResponseError(
                "Featherless returned an invalid PatchProposal",
                raw=raw,
                detail=detail,
            ) from exc

    @staticmethod
    def _repair_payload(
        payload: dict[str, Any],
        error: FeatherResponseError,
    ) -> dict[str, Any]:
        messages = list(payload["messages"])
        if error.raw:
            messages.append({"role": "assistant", "content": error.raw})
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "repair": "Return only a corrected JSON object.",
                        "validation_error": error.detail,
                    },
                    sort_keys=True,
                ),
            }
        )
        return {**payload, "messages": messages}

    @staticmethod
    async def _report(
        reporter: TechnicalErrorReporter | None,
        error: ModelTechnicalError,
    ) -> None:
        if reporter is not None:
            await reporter(error)

    @staticmethod
    def _backoff_seconds(request_number: int) -> float:
        return min(2 ** (request_number - 1), 4)

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


def extract_json_object(raw: str) -> object:
    decoder = json.JSONDecoder()
    stripped = raw.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as initial_error:
        for start, character in enumerate(stripped):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(stripped, start)
                return value
            except json.JSONDecodeError:
                continue
        raise initial_error
