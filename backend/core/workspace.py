from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Literal


_SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


class WorkspaceError(RuntimeError):
    pass


class WorkspaceExistsError(WorkspaceError):
    pass


def read_text(
    path: Path,
    *,
    errors: Literal["strict", "surrogateescape"] = "strict",
) -> str:
    data = path.read_bytes()
    return data.decode("utf-8", errors=errors).replace("\r\n", "\n").replace("\r", "\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.encode("utf-8"))


class WorkspaceManager:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        git = shutil.which("git")
        if git is None:
            raise WorkspaceError("git executable not found")
        self._git = git

    def materialize(
        self,
        source: str | Path,
        base_sha: str,
        job_id: str,
    ) -> Path:
        job_root = self._job_root(job_id)
        base = job_root / "base"
        if base.exists():
            raise WorkspaceExistsError(f"base workspace already exists for {job_id}")

        job_root.mkdir(parents=True, exist_ok=True)
        try:
            self._run_git(
                "clone",
                "--depth",
                "1",
                "--no-checkout",
                "--no-hardlinks",
                str(source),
                str(base),
            )
            # This must be repository-local and set before checkout or Git may
            # rewrite committed LF bytes on Windows.
            self._run_git("config", "core.autocrlf", "false", cwd=base)
            self._run_git("checkout", "--detach", base_sha, cwd=base)
        except Exception:
            if base.exists():
                shutil.rmtree(base)
            raise
        return base

    def create_candidate(self, job_id: str, attempt_number: int) -> Path:
        if attempt_number < 1:
            raise ValueError("attempt number must be positive")

        job_root = self._job_root(job_id)
        base = job_root / "base"
        if not base.is_dir():
            raise WorkspaceError(f"base workspace does not exist for {job_id}")

        candidate = job_root / f"candidate-{attempt_number}"
        if candidate.exists():
            raise WorkspaceExistsError(
                f"candidate {attempt_number} already exists for {job_id}"
            )
        shutil.copytree(base, candidate, symlinks=True)
        return candidate

    def cleanup_candidate(self, candidate: Path) -> None:
        resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError("candidate path escapes the workspace root") from exc

        if len(relative.parts) != 2 or not relative.name.startswith("candidate-"):
            raise WorkspaceError("refusing to remove a non-candidate workspace")
        if resolved.exists():
            shutil.rmtree(resolved)

    def _job_root(self, job_id: str) -> Path:
        if job_id in {".", ".."} or _SAFE_JOB_ID.fullmatch(job_id) is None:
            raise ValueError(f"unsafe job id: {job_id!r}")
        return self.root / job_id

    def _run_git(self, *args: str, cwd: Path | None = None) -> None:
        environment = {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "AegisAgent",
            "GIT_AUTHOR_EMAIL": "aegis@example.invalid",
            "GIT_COMMITTER_NAME": "AegisAgent",
            "GIT_COMMITTER_EMAIL": "aegis@example.invalid",
            "LC_ALL": "C",
        }
        result = subprocess.run(
            [self._git, *args],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise WorkspaceError(f"git command failed: {detail}")
