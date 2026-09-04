from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatherSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
