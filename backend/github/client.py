from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import quote

import httpx

from backend.core.config import GitHubSettings


class GitHubDeliveryError(RuntimeError):
    pass


class GitHubConfigurationError(GitHubDeliveryError):
    pass


class GitHubBaseMismatchError(GitHubDeliveryError):
    pass


class GitHubProviderError(GitHubDeliveryError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class PullRequestResult:
    url: str
    number: int
    branch: str


class GitHubClient:
    """Deliver verified file contents through GitHub's REST Git Data API."""

    def __init__(
        self,
        settings: GitHubSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self._sleep = sleep

    async def create_pull_request(
        self,
        *,
        expected_base_sha: str,
        branch: str,
        files: Mapping[str, str],
        title: str,
        body: str,
        commit_message: str,
    ) -> PullRequestResult:
        owner, repo, token = self._configuration()
        repository = f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(
            base_url=self.settings.api_url.rstrip("/"),
            headers=headers,
            timeout=self.settings.timeout_seconds,
            transport=self._transport,
        ) as client:
            base_ref = await self._request_json(
                client,
                "GET",
                f"{repository}/git/ref/heads/{quote(self.settings.base_branch, safe='')}",
            )
            remote_base_sha = _nested_string(base_ref, "object", "sha")
            if remote_base_sha != expected_base_sha:
                raise GitHubBaseMismatchError(
                    "configured GitHub base does not match the verified base commit"
                )

            commit = await self._request_json(
                client,
                "GET",
                f"{repository}/git/commits/{quote(remote_base_sha, safe='')}",
            )
            base_tree_sha = _nested_string(commit, "tree", "sha")
            tree_items: list[dict[str, str]] = []
            for path, content in sorted(files.items()):
                blob = await self._request_json(
                    client,
                    "POST",
                    f"{repository}/git/blobs",
                    json={"content": _lf(content), "encoding": "utf-8"},
                )
                tree_items.append(
                    {
                        "path": path.replace("\\", "/"),
                        "mode": "100644",
                        "type": "blob",
                        "sha": _required_string(blob, "sha"),
                    }
                )

            tree = await self._request_json(
                client,
                "POST",
                f"{repository}/git/trees",
                json={"base_tree": base_tree_sha, "tree": tree_items},
            )
            created_commit = await self._request_json(
                client,
                "POST",
                f"{repository}/git/commits",
                json={
                    "message": commit_message,
                    "tree": _required_string(tree, "sha"),
                    "parents": [remote_base_sha],
                },
            )
            commit_sha = _required_string(created_commit, "sha")
            await self._request_json(
                client,
                "POST",
                f"{repository}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
            )
            pull = await self._request_json(
                client,
                "POST",
                f"{repository}/pulls",
                json={
                    "title": title,
                    "body": body,
                    "head": branch,
                    "base": self.settings.base_branch,
                },
            )
        return PullRequestResult(
            url=_required_string(pull, "html_url"),
            number=_required_int(pull, "number"),
            branch=branch,
        )

    def _configuration(self) -> tuple[str, str, str]:
        token = self.settings.token
        if token is None or not self.settings.owner or not self.settings.repo:
            raise GitHubConfigurationError(
                "GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO are required for delivery"
            )
        return (
            self.settings.owner,
            self.settings.repo,
            token.get_secret_value(),
        )

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        max_requests = self.settings.transport_retries + 1
        for request_number in range(1, max_requests + 1):
            try:
                response = await client.request(method, path, json=json)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                error = GitHubProviderError(
                    f"GitHub REST delivery returned HTTP {status}",
                    retryable=status == 429 or status >= 500,
                )
            except httpx.HTTPError:
                error = GitHubProviderError(
                    "GitHub REST transport failed",
                    retryable=True,
                )
            except ValueError as exc:
                raise GitHubDeliveryError(
                    "GitHub returned an invalid JSON response"
                ) from exc
            else:
                if not isinstance(payload, dict):
                    raise GitHubDeliveryError("GitHub returned a non-object response")
                return payload

            if not error.retryable or request_number == max_requests:
                raise error
            await self._sleep(min(2 ** (request_number - 1), 4))

        raise AssertionError("bounded GitHub request loop did not terminate")


def _lf(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise GitHubDeliveryError(f"GitHub response omitted {key}")
    return value


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise GitHubDeliveryError(f"GitHub response omitted {key}")
    return value


def _nested_string(payload: dict[str, Any], parent: str, key: str) -> str:
    nested = payload.get(parent)
    if not isinstance(nested, dict):
        raise GitHubDeliveryError(f"GitHub response omitted {parent}")
    return _required_string(nested, key)
