from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
)


class FeatherSettings(BaseSettings):
    model_config = _ENV_CONFIG

    api_key: SecretStr = Field(alias="FEATHER_API_KEY")
    base_url: str = Field(
        default="https://api.featherless.ai/v1",
        alias="FEATHER_BASE_URL",
    )
    model: str = Field(default="moonshotai/Kimi-K3", alias="AEGIS_MODEL")
    max_tokens: int = Field(default=8_000, gt=0, alias="AEGIS_MODEL_MAX_TOKENS")
    temperature: float = Field(default=0.0, ge=0.0, alias="AEGIS_MODEL_TEMPERATURE")
    timeout_seconds: float = Field(default=60.0, gt=0, alias="AEGIS_LLM_TIMEOUT_S")
    concurrency: int = Field(default=1, ge=1, alias="AEGIS_LLM_CONCURRENCY")
    transport_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        alias="AEGIS_LLM_TRANSPORT_RETRIES",
    )


class RuntimeSettings(BaseSettings):
    model_config = _ENV_CONFIG

    db_path: Path = Field(default=Path("aegis.db"), alias="AEGIS_DB_PATH")
    workspace_root: Path = Field(
        default=Path(".workspaces"),
        alias="AEGIS_WORKSPACE_ROOT",
    )
    policy_path: Path = Field(
        default=Path("policies/security_policy.json"),
        alias="AEGIS_POLICY_PATH",
    )
    max_attempts: int = Field(default=3, ge=1, le=10, alias="AEGIS_MAX_ATTEMPTS")
    job_wall_clock_seconds: float = Field(
        default=480.0,
        gt=0,
        alias="AEGIS_JOB_WALL_CLOCK_S",
    )


class GitHubSettings(BaseSettings):
    model_config = _ENV_CONFIG

    token: SecretStr | None = Field(default=None, alias="GITHUB_TOKEN")
    owner: str | None = Field(default=None, alias="GITHUB_OWNER")
    repo: str | None = Field(default=None, alias="GITHUB_REPO")
    base_branch: str = Field(default="main", alias="GITHUB_BASE_BRANCH")
    api_url: str = Field(default="https://api.github.com", alias="GITHUB_API_URL")
    timeout_seconds: float = Field(default=30.0, gt=0, alias="GITHUB_TIMEOUT_S")
    transport_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        alias="GITHUB_TRANSPORT_RETRIES",
    )


def sandbox_env(home: Path, *, executable_path: str = "") -> dict[str, str]:
    environment = {
        "PATH": executable_path,
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(home),
        "TEMP": str(home),
        "TMP": str(home),
        "AEGIS_SANDBOX": "1",
    }
    if os.name == "nt":
        # CreateProcess needs SystemRoot on Windows; it is the sole host value
        # copied into the otherwise constructed environment.
        environment["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
    return environment
