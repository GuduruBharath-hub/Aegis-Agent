from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.adapters.base import AdapterName
from backend.core.workspace import read_text, write_text
from backend.sandbox.docker_backend import DockerBackend, DockerExecution


class SandboxRunnerError(RuntimeError):
    pass


class SandboxReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = Field(alias="schema")
    attack: dict[str, Any]
    pytest: dict[str, Any]
    bandit: dict[str, Any]
    durations: dict[str, int]
    python_version: str


@dataclass(frozen=True, slots=True)
class SandboxRun:
    tier: Literal["docker"]
    report: SandboxReport
    exit_code: int
    stderr: str
    duration_ms: int


class SandboxRunner:
    def __init__(
        self,
        project_root: Path,
        backend: DockerBackend | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.backend = backend or DockerBackend()

    def ensure_image(self) -> None:
        self.backend.ensure_image(self.project_root / "backend" / "sandbox" / "image")

    def run(
        self,
        candidate: Path,
        *,
        adapter: AdapterName,
        timeout_seconds: int = 90,
    ) -> SandboxRun:
        with tempfile.TemporaryDirectory(prefix="aegis-runtime-") as temporary:
            runtime = Path(temporary)
            self._stage_runtime(runtime, adapter)
            execution = self.backend.run(
                candidate,
                runtime,
                timeout_seconds=timeout_seconds,
            )
        return self._parse_execution(execution)

    def _stage_runtime(self, runtime: Path, adapter: str) -> None:
        payload = self.project_root / "backend" / "sandbox" / "payload"
        harnesses = {
            "sql_injection": self.project_root
            / "aegis_hidden_tests"
            / "sql_injection"
            / "harness.py",
            "command_injection": self.project_root
            / "aegis_hidden_tests"
            / "command_injection"
            / "harness.py",
        }
        harness = harnesses.get(adapter)
        if harness is None:
            raise SandboxRunnerError(f"unsupported sandbox adapter: {adapter}")

        write_text(runtime / "run_all.py", read_text(payload / "run_all.py"))
        write_text(runtime / "sitecustomize.py", read_text(payload / "sitecustomize.py"))
        write_text(runtime / "harness.py", read_text(harness))

    def _parse_execution(self, execution: DockerExecution) -> SandboxRun:
        if execution.exit_code != 0:
            raise SandboxRunnerError(
                f"sandbox harness failed with exit code {execution.exit_code}: "
                f"{execution.stderr.strip()}"
            )
        try:
            report = SandboxReport.model_validate_json(execution.stdout)
        except ValueError as exc:
            raise SandboxRunnerError("sandbox returned an invalid report") from exc
        return SandboxRun(
            tier="docker",
            report=report,
            exit_code=execution.exit_code,
            stderr=execution.stderr,
            duration_ms=execution.duration_ms,
        )
