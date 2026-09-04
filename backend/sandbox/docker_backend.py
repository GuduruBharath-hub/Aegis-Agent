from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import perf_counter

from backend.core.config import sandbox_env


class DockerSandboxError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DockerExecution:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class DockerBackend:
    def __init__(self, image: str = "aegis-sandbox:py311") -> None:
        docker = shutil.which("docker")
        if docker is None:
            raise DockerSandboxError("docker executable not found")
        self.image = image
        self._docker = docker

    def ensure_image(self, dockerfile_directory: Path) -> None:
        inspected = self._command(
            ["image", "inspect", self.image],
            timeout=30,
        )
        if inspected.returncode == 0:
            return
        built = self._command(
            ["build", "--tag", self.image, str(dockerfile_directory.resolve())],
            timeout=300,
        )
        if built.returncode != 0:
            detail = built.stderr.strip() or built.stdout.strip()
            raise DockerSandboxError(f"sandbox image build failed: {detail}")

    def run(
        self,
        candidate: Path,
        runtime: Path,
        *,
        timeout_seconds: int = 90,
    ) -> DockerExecution:
        candidate_root = candidate.resolve()
        runtime_root = runtime.resolve()
        mount_target = candidate_root / "_aegis_runtime"
        if mount_target.exists():
            raise DockerSandboxError("candidate already contains _aegis_runtime")

        mount_target.mkdir()
        command = [
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m,mode=1777",
            "--tmpfs",
            "/out:rw,noexec,nosuid,size=16m,mode=1777",
            "--mount",
            f"type=bind,source={candidate_root},target=/work",
            "--mount",
            f"type=bind,source={runtime_root},target=/work/_aegis_runtime,readonly",
            "--user",
            "65534:65534",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            "512m",
            "--cpus",
            "1.0",
            "--env",
            "PYTHONPATH=/work/_aegis_runtime:/work",
            "--env",
            "PYTHONHASHSEED=0",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "HOME=/tmp",
            "--env",
            "AEGIS_SANDBOX=1",
            self.image,
            "timeout",
            str(timeout_seconds),
            "python",
            "/work/_aegis_runtime/run_all.py",
        ]
        started = perf_counter()
        try:
            result = self._command(command, timeout=timeout_seconds + 15)
        finally:
            # Docker needs the empty target to layer the read-only runtime mount;
            # removing it keeps hidden-test paths out of the candidate afterward.
            if mount_target.exists():
                mount_target.rmdir()
        return DockerExecution(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=round((perf_counter() - started) * 1000),
        )

    def _command(
        self,
        arguments: list[str],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="aegis-docker-home-") as home:
            try:
                return subprocess.run(
                    [self._docker, *arguments],
                    env=sandbox_env(
                        Path(home),
                        executable_path=str(Path(self._docker).parent),
                    ),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise DockerSandboxError("docker command exceeded its timeout") from exc
