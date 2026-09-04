from __future__ import annotations

import os
from pathlib import Path
import re

import pytest

from backend.core.config import sandbox_env


SENSITIVE_KEY = re.compile(r"TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL", re.IGNORECASE)


def test_sandbox_environment_excludes_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "must-not-reach-untrusted-code"
    for name in (
        "GITHUB_TOKEN",
        "FEATHER_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "DATABASE_PASSWORD",
        "CLOUD_CREDENTIAL",
    ):
        monkeypatch.setenv(name, sentinel)

    environment = sandbox_env(tmp_path, executable_path="/safe/bin")

    assert not {name for name in environment if SENSITIVE_KEY.search(name)}
    assert sentinel not in environment.values()
    assert environment["HOME"] == str(tmp_path)
    assert environment["PATH"] == "/safe/bin"
    assert set(environment) == {
        "PATH",
        "PYTHONHASHSEED",
        "PYTHONDONTWRITEBYTECODE",
        "HOME",
        "TEMP",
        "TMP",
        "AEGIS_SANDBOX",
        *({"SYSTEMROOT"} if os.name == "nt" else set()),
    }
