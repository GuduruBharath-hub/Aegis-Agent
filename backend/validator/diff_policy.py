from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Literal

from backend.core.models import DiffStats, PolicyViolation
from backend.core.workspace import read_text
from backend.validator.protected_paths import PathEscapeError, normalize_relative_path


ChangeKind = Literal["modified", "added", "deleted"]


@dataclass(frozen=True, slots=True)
class FileChange:
    path: str
    kind: ChangeKind
    lines_added: int = 0
    lines_removed: int = 0
    binary: bool = False
    symbolic_link: bool = False
    path_escape: bool = False


def compare_trees(base: Path, candidate: Path) -> tuple[FileChange, ...]:
    base_root = base.resolve()
    candidate_root = candidate.resolve()
    base_entries = _tree_entries(base_root)
    candidate_entries = _tree_entries(candidate_root)
    changes: list[FileChange] = []

    for relative in sorted(base_entries.keys() | candidate_entries.keys()):
        before = base_entries.get(relative)
        after = candidate_entries.get(relative)
        kind: ChangeKind = (
            "added" if before is None else "deleted" if after is None else "modified"
        )

        if _unchanged_links(before, after):
            continue
        if (before is not None and before.is_symlink()) or (
            after is not None and after.is_symlink()
        ):
            changes.append(
                FileChange(relative, kind, symbolic_link=True)
            )
            continue

        try:
            if before is not None:
                normalize_relative_path(base_root, relative)
            if after is not None:
                normalize_relative_path(candidate_root, relative)
        except PathEscapeError:
            changes.append(FileChange(relative, kind, path_escape=True))
            continue

        old_content, old_binary = _content(before)
        new_content, new_binary = _content(after)
        if old_content == new_content and old_binary == new_binary:
            continue

        binary = old_binary or new_binary
        if binary:
            changes.append(FileChange(relative, kind, binary=True))
            continue

        added, removed = _line_delta(old_content, new_content)
        changes.append(
            FileChange(
                relative,
                kind,
                lines_added=added,
                lines_removed=removed,
            )
        )
    return tuple(changes)


def diff_stats(changes: tuple[FileChange, ...]) -> DiffStats:
    return DiffStats(
        files_changed=len(changes),
        lines_added=sum(change.lines_added for change in changes),
        lines_removed=sum(change.lines_removed for change in changes),
    )


def render_unified_diff(base: Path, candidate: Path) -> str:
    """Render the validator's actual tree comparison for durable review."""
    sections: list[str] = []
    for change in compare_trees(base, candidate):
        if change.symbolic_link:
            sections.append(f"Symbolic link {change.path} changed\n")
            continue
        if change.path_escape:
            sections.append(f"Unsafe path {change.path} changed\n")
            continue

        before = None if change.kind == "added" else base / change.path
        after = None if change.kind == "deleted" else candidate / change.path
        old_content, old_binary = _content(before)
        new_content, new_binary = _content(after)
        if old_binary or new_binary:
            sections.append(
                f"Binary files a/{change.path} and b/{change.path} differ\n"
            )
            continue
        from_file = "/dev/null" if before is None else f"a/{change.path}"
        to_file = "/dev/null" if after is None else f"b/{change.path}"
        lines = unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=from_file,
            tofile=to_file,
            lineterm="",
        )
        sections.extend(f"{line}\n" for line in lines)
    return "".join(sections)


def find_diff_violations(
    changes: tuple[FileChange, ...],
    *,
    max_files_changed: int,
    max_changed_lines: int,
    allow_new_files: bool,
    allow_file_deletion: bool,
) -> tuple[PolicyViolation, ...]:
    stats = diff_stats(changes)
    violations: list[PolicyViolation] = []
    if stats.files_changed > max_files_changed:
        violations.append(
            PolicyViolation(
                "max_files_changed",
                f"candidate changes {stats.files_changed} files; limit is {max_files_changed}",
            )
        )
    if stats.changed_lines > max_changed_lines:
        violations.append(
            PolicyViolation(
                "max_changed_lines",
                f"candidate changes {stats.changed_lines} lines; limit is {max_changed_lines}",
            )
        )

    for change in changes:
        if change.kind == "added" and not allow_new_files:
            violations.append(
                PolicyViolation("new_file", "new files are not allowed", path=change.path)
            )
        if change.kind == "deleted" and not allow_file_deletion:
            violations.append(
                PolicyViolation(
                    "file_deletion", "file deletion is not allowed", path=change.path
                )
            )
        if change.binary:
            violations.append(
                PolicyViolation(
                    "binary_file", "binary file changes are not allowed", path=change.path
                )
            )
        if change.symbolic_link:
            violations.append(
                PolicyViolation(
                    "symbolic_link",
                    "symbolic link changes are not allowed",
                    path=change.path,
                )
            )
    return tuple(violations)


def _tree_entries(root: Path) -> dict[str, Path]:
    entries: dict[str, Path] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if path.is_file() or path.is_symlink():
            entries[relative.as_posix()] = path
    return entries


def _unchanged_links(before: Path | None, after: Path | None) -> bool:
    return (
        before is not None
        and after is not None
        and before.is_symlink()
        and after.is_symlink()
        and before.readlink() == after.readlink()
    )


def _content(path: Path | None) -> tuple[str, bool]:
    if path is None:
        return "", False
    content = read_text(path, errors="surrogateescape")
    binary = "\x00" in content or any(
        0xDC80 <= ord(character) <= 0xDCFF for character in content
    )
    return content, binary


def _line_delta(old_content: str, new_content: str) -> tuple[int, int]:
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    matcher = SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    added = 0
    removed = 0
    for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if operation == "equal":
            continue
        removed += old_end - old_start
        added += new_end - new_start
    return added, removed
