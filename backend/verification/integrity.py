from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from backend.core.workspace import read_text


_EXCLUDED_PARTS = frozenset(
    {".git", "_aegis_runtime", "__pycache__", ".pytest_cache"}
)


@dataclass(frozen=True, slots=True)
class IntegrityResult:
    passed: bool
    pre_run: str
    post_run: str
    delivery: str
    reason: str


def tree_hash(root: Path) -> str:
    workspace = root.resolve()
    entries: list[str] = []
    for path in sorted(workspace.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(workspace)
        if _excluded(relative):
            continue
        if path.is_symlink():
            # Hash the link itself; following it could read outside the workspace
            # and would fail to detect a changed delivery-time link target.
            data = f"symlink:{path.readlink().as_posix()}".encode("utf-8")
        elif path.is_dir():
            continue
        else:
            content = read_text(path, errors="surrogateescape")
            normalized = content.replace("\r\n", "\n").replace("\r", "\n")
            data = normalized.encode("utf-8", errors="surrogateescape")
        digest = hashlib.sha256(data).hexdigest()
        entries.append(f"{digest}  {relative.as_posix()}")
    manifest = "\n".join(entries).encode("utf-8")
    return hashlib.sha256(manifest).hexdigest()


def compare(pre_run: str, post_run: str, delivery: str) -> IntegrityResult:
    passed = pre_run == post_run == delivery
    return IntegrityResult(
        passed=passed,
        pre_run=pre_run,
        post_run=post_run,
        delivery=delivery,
        reason=(
            "all three tree hashes match"
            if passed
            else "pre-run, post-run, and delivery tree hashes must match"
        ),
    )


def _excluded(relative: Path) -> bool:
    return any(part in _EXCLUDED_PARTS for part in relative.parts)
