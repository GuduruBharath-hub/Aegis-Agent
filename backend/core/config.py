from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import dotenv_values
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
    replay_dir: Path = Field(default=Path("replay"), alias="AEGIS_REPLAY_DIR")
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


@dataclass(frozen=True, slots=True)
class ModelSlot:
    """One provider in the failover chain.

    Every supported provider speaks the OpenAI chat-completions protocol, so a
    slot is pure configuration: base URL, key, model id. No provider needs its
    own client.
    """

    label: str
    api_key: SecretStr
    base_url: str
    model: str
    max_tokens: int
    temperature: float
    timeout_seconds: float
    concurrency: int
    transport_retries: int


class ModelChainError(RuntimeError):
    pass


_SLOT_ENV: tuple[tuple[str, str, str, str], ...] = (
    ("primary", "AEGIS_MODEL_1_API_KEY", "AEGIS_MODEL_1_BASE_URL", "AEGIS_MODEL_1_NAME"),
    ("fallback-1", "AEGIS_MODEL_2_API_KEY", "AEGIS_MODEL_2_BASE_URL", "AEGIS_MODEL_2_NAME"),
    ("fallback-2", "AEGIS_MODEL_3_API_KEY", "AEGIS_MODEL_3_BASE_URL", "AEGIS_MODEL_3_NAME"),
)


def load_model_chain(environ: dict[str, str] | None = None) -> tuple[ModelSlot, ...]:
    """Build the ordered provider chain from the environment.

    A slot is enabled only when its API key, base URL and model id are all
    present; a half-configured slot is skipped rather than being allowed to
    fail at demo time. Slot 1 falls back to the legacy FEATHER_* names so an
    existing .env keeps working unchanged.

    Reads .env as well as the process environment, matching the BaseSettings
    classes above. Reading only os.environ would silently ignore a correctly
    filled .env and report "no provider configured".
    """
    if environ is None:
        env = {
            **{k: v for k, v in dotenv_values(_ENV_CONFIG["env_file"]).items() if v is not None},
            **os.environ,  # a real environment variable overrides the file
        }
    else:
        env = environ

    def shared(name: str, default: str) -> str:
        value = env.get(name, "").strip()
        return value or default

    max_tokens = int(shared("AEGIS_MODEL_MAX_TOKENS", "8000"))
    temperature = float(shared("AEGIS_MODEL_TEMPERATURE", "0"))
    timeout_seconds = float(shared("AEGIS_LLM_TIMEOUT_S", "60"))
    concurrency = int(shared("AEGIS_LLM_CONCURRENCY", "1"))
    transport_retries = int(shared("AEGIS_LLM_TRANSPORT_RETRIES", "2"))

    slots: list[ModelSlot] = []
    for index, (label, key_var, url_var, model_var) in enumerate(_SLOT_ENV):
        api_key = env.get(key_var, "").strip()
        base_url = env.get(url_var, "").strip()
        model = env.get(model_var, "").strip()
        if index == 0:
            api_key = api_key or env.get("FEATHER_API_KEY", "").strip()
            base_url = base_url or env.get("FEATHER_BASE_URL", "").strip()
            model = model or env.get("AEGIS_MODEL", "").strip()
        if not (api_key and base_url and model):
            continue
        slots.append(
            ModelSlot(
                label=label,
                api_key=SecretStr(api_key),
                base_url=base_url,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                concurrency=concurrency,
                transport_retries=transport_retries,
            )
        )

    if not slots:
        raise ModelChainError(
            "No model provider is configured. Set AEGIS_MODEL_1_API_KEY, "
            "AEGIS_MODEL_1_BASE_URL and AEGIS_MODEL_1_NAME in .env "
            "(see .env.example)."
        )
    return tuple(slots)


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
