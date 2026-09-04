from __future__ import annotations

import os
from pathlib import Path


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
