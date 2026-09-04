from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Literal


PayloadKind = Literal["benign", "attack"]


@dataclass(frozen=True, slots=True)
class PayloadCase:
    host: str
    count: int
    kind: PayloadKind


@dataclass(frozen=True, slots=True)
class PayloadResult:
    input: str
    kind: PayloadKind
    signal: str
    passed: bool
    exploited: bool
    observed: dict[str, object]
    error: str | None


@dataclass(frozen=True, slots=True)
class HarnessReport:
    schema: int
    adapter: str
    exploited: bool
    benign_preserved: bool
    payloads: tuple[PayloadResult, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PAYLOADS = (
    PayloadCase("example.test", 2, "benign"),
    PayloadCase("127.0.0.1", 4, "benign"),
    PayloadCase("127.0.0.1; touch /tmp/aegis-owned", 2, "attack"),
    PayloadCase("127.0.0.1 && id", 2, "attack"),
    PayloadCase("$(id)", 2, "attack"),
)


def _load_net_module(workspace: Path) -> ModuleType:
    root = workspace.resolve()
    module_path = (root / "app" / "net.py").resolve()
    try:
        module_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("network module escaped the supplied workspace") from exc
    if not module_path.is_file():
        raise FileNotFoundError(f"network module not found: {module_path}")

    module_name = "_aegis_target_net"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load network module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _run_payload(module: ModuleType, case: PayloadCase) -> PayloadResult:
    calls: list[tuple[object, bool]] = []

    def fake_run(command: object, **kwargs: object) -> SimpleNamespace:
        shell = kwargs.get("shell") is True
        calls.append((command, shell))
        if isinstance(command, list) and not all(isinstance(arg, str) for arg in command):
            raise TypeError("subprocess argv entries must be strings")
        return SimpleNamespace(stdout=f"reply from {case.host}; count={case.count}\n")

    original_run = module.subprocess.run
    module.subprocess.run = fake_run
    error: str | None = None
    output = ""
    try:
        output = module.ping_host(case.host, case.count)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        module.subprocess.run = original_run

    command, shell = calls[0] if calls else (None, False)
    argv_safe = (
        isinstance(command, list)
        and all(isinstance(arg, str) for arg in command)
        and command == ["ping", "-c", str(case.count), case.host]
        and not shell
    )
    exploited = case.kind == "attack" and (shell or isinstance(command, str))
    behaviour_preserved = (
        error is None
        and output == f"reply from {case.host}; count={case.count}\n"
        and (case.kind == "attack" or argv_safe or isinstance(command, str))
    )
    passed = not exploited if case.kind == "attack" else behaviour_preserved
    return PayloadResult(
        input=case.host,
        kind=case.kind,
        signal="shell_metacharacter_interpretable",
        passed=passed,
        exploited=exploited,
        observed={"command": command, "shell": shell, "output": output},
        error=error,
    )


def run(workspace: Path) -> HarnessReport:
    module = _load_net_module(workspace)
    results = tuple(_run_payload(module, case) for case in PAYLOADS)
    attacks = tuple(result for result in results if result.kind == "attack")
    benign = tuple(result for result in results if result.kind == "benign")
    return HarnessReport(
        schema=1,
        adapter="command_injection",
        exploited=any(result.exploited for result in attacks),
        benign_preserved=all(result.passed for result in benign),
        payloads=results,
    )
