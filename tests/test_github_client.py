from __future__ import annotations

import asyncio
import json

import httpx
from pydantic import SecretStr
import pytest

from backend.core.config import GitHubSettings
from backend.github.client import (
    GitHubBaseMismatchError,
    GitHubClient,
    GitHubProviderError,
)


BASE_SHA = "a" * 40
TOKEN = "github-secret-value"


def _settings() -> GitHubSettings:
    return GitHubSettings(
        GITHUB_TOKEN=SecretStr(TOKEN),
        GITHUB_OWNER="example",
        GITHUB_REPO="vulnerable-demo",
        GITHUB_BASE_BRANCH="main",
    )


def test_delivery_uses_rest_git_data_sequence_and_authorization_header() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASE_SHA}})
        if path.endswith(f"/git/commits/{BASE_SHA}"):
            return httpx.Response(200, json={"tree": {"sha": "base-tree"}})
        if path.endswith("/git/blobs"):
            return httpx.Response(201, json={"sha": f"blob-{len(requests)}"})
        if path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "new-tree"})
        if path.endswith("/git/commits"):
            return httpx.Response(201, json={"sha": "new-commit"})
        if path.endswith("/git/refs"):
            return httpx.Response(201, json={"ref": "refs/heads/aegis/finding-cwe89"})
        if path.endswith("/pulls"):
            return httpx.Response(
                201,
                json={"html_url": "https://github.com/example/demo/pull/7", "number": 7},
            )
        return httpx.Response(404)

    client = GitHubClient(_settings(), transport=httpx.MockTransport(handler))
    result = asyncio.run(
        client.create_pull_request(
            expected_base_sha=BASE_SHA,
            branch="aegis/finding-cwe89",
            files={"app/database.py": "first\r\nsecond\r"},
            title="Fix CWE-89",
            body="Verified by six gates.",
            commit_message="fix: remediate CWE-89",
        )
    )

    assert result.url.endswith("/pull/7")
    assert result.number == 7
    assert [request.method for request in requests] == [
        "GET", "GET", "POST", "POST", "POST", "POST", "POST"
    ]
    assert all(request.headers["authorization"] == f"Bearer {TOKEN}" for request in requests)
    assert all(TOKEN not in str(request.url) for request in requests)
    assert all(TOKEN.encode() not in request.content for request in requests)
    blob_payload = json.loads(requests[2].content)
    assert blob_payload == {"content": "first\nsecond\n", "encoding": "utf-8"}
    assert json.loads(requests[5].content) == {
        "ref": "refs/heads/aegis/finding-cwe89",
        "sha": "new-commit",
    }


def test_base_mismatch_stops_before_any_github_write() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"object": {"sha": "b" * 40}})

    client = GitHubClient(_settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(GitHubBaseMismatchError):
        asyncio.run(
            client.create_pull_request(
                expected_base_sha=BASE_SHA,
                branch="aegis/finding-cwe89",
                files={"app.py": "safe = True\n"},
                title="Fix",
                body="Evidence",
                commit_message="Fix",
            )
        )

    assert len(requests) == 1
    assert requests[0].method == "GET"


def test_transient_github_failure_retries_with_bounded_backoff() -> None:
    requests: list[httpx.Request] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503)
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASE_SHA}})
        if request.url.path.endswith(f"/git/commits/{BASE_SHA}"):
            return httpx.Response(200, json={"tree": {"sha": "base-tree"}})
        if request.url.path.endswith("/git/blobs"):
            return httpx.Response(201, json={"sha": "blob"})
        if request.url.path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "tree"})
        if request.url.path.endswith("/git/commits"):
            return httpx.Response(201, json={"sha": "commit"})
        if request.url.path.endswith("/git/refs"):
            return httpx.Response(201, json={"ref": "refs/heads/aegis/finding-cwe89"})
        if request.url.path.endswith("/pulls"):
            return httpx.Response(
                201,
                json={"html_url": "https://github.com/example/demo/pull/8", "number": 8},
            )
        return httpx.Response(404)

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = GitHubClient(
        _settings(),
        transport=httpx.MockTransport(handler),
        sleep=record_sleep,
    )
    asyncio.run(
        client.create_pull_request(
            expected_base_sha=BASE_SHA,
            branch="aegis/finding-cwe89",
            files={"app.py": "safe = True\n"},
            title="Fix",
            body="Evidence",
            commit_message="Fix",
        )
    )

    assert sleeps == [1]
    assert len(requests) == 8


def test_persistent_github_failure_stops_at_retry_limit() -> None:
    request_count = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(503)

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = GitHubClient(
        _settings(),
        transport=httpx.MockTransport(handler),
        sleep=record_sleep,
    )
    with pytest.raises(GitHubProviderError):
        asyncio.run(
            client.create_pull_request(
                expected_base_sha=BASE_SHA,
                branch="aegis/finding-cwe89",
                files={"app.py": "safe = True\n"},
                title="Fix",
                body="Evidence",
                commit_message="Fix",
            )
        )

    assert request_count == 3
    assert sleeps == [1, 2]
