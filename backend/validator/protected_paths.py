from __future__ import annotations

from collections.abc import Iterable
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath, PureWindowsPath

from backend.core.models import PolicyViolation


class PathEscapeError(ValueError):
    pass


def normalize_relative_path(root: Path, untrusted_path: str | Path) -> str:
    raw = str(untrusted_path)
    windows_path = PureWindowsPath(raw)
    portable = PurePosixPath(raw.replace("\\", "/"))
    if portable.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise PathEscapeError(f"absolute path is not allowed: {raw}")

    resolved_root = root.resolve()
    resolved = (resolved_root / Path(*portable.parts)).resolve()
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PathEscapeError(f"path escapes workspace: {raw}") from exc
    return relative.as_posix()


def find_protected_path_violations(
    root: Path,
    paths: Iterable[str],
    patterns: tuple[str, ...],
) -> tuple[PolicyViolation, ...]:
    violations: list[PolicyViolation] = []
    for path in sorted(set(paths)):
        try:
            normalized = normalize_relative_path(root, path)
        except PathEscapeError as exc:
            violations.append(
                PolicyViolation("path_escape", str(exc), path=path)
            )
            continue

        if any(_matches(normalized, pattern) for pattern in patterns):
            violations.append(
                PolicyViolation(
                    "protected_path",
                    "candidate modifies a protected path",
                    path=normalized,
                )
            )
    return tuple(violations)


def _matches(path: str, pattern: str) -> bool:
    if fnmatchcase(path, pattern):
        return True
    # A leading **/ means zero or more directories in the policy, so it must
    # also match a protected file at the repository root.
    return pattern.startswith("**/") and fnmatchcase(path, pattern[3:])
