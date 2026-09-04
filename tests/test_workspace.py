from __future__ import annotations

import hashlib
import os
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from backend.core.workspace import (
    WorkspaceError,
    WorkspaceExistsError,
    WorkspaceManager,
    _remove_readonly,
    read_text,
    write_text,
)


def _run_git(cwd: Path, *args: str) -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git executable not found")
    result = subprocess.run(
        [git, *args],
        cwd=cwd,
        env={
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Aegis Test",
            "GIT_AUTHOR_EMAIL": "aegis-test@example.invalid",
            "GIT_COMMITTER_NAME": "Aegis Test",
            "GIT_COMMITTER_EMAIL": "aegis-test@example.invalid",
            "LC_ALL": "C",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _content_hash(path: Path) -> str:
    return hashlib.sha256(read_text(path).encode("utf-8")).hexdigest()


def _committed_repository(root: Path) -> tuple[Path, str]:
    repository = root / "source"
    repository.mkdir()
    _run_git(repository, "init")
    _run_git(repository, "config", "core.autocrlf", "false")
    write_text(repository / "app.py", "first line\r\nsecond line\r")
    expected_hash = _content_hash(repository / "app.py")
    _run_git(repository, "add", "app.py")
    _run_git(repository, "commit", "-m", "fixture")

    write_text(repository / "app.py", "temporary change\r\n")
    _run_git(repository, "checkout", "HEAD", "--", "app.py")
    assert _content_hash(repository / "app.py") == expected_hash
    return repository, _run_git(repository, "rev-parse", "HEAD")


def test_git_round_trip_and_candidates_preserve_immutable_base(
    tmp_path: Path,
) -> None:
    repository, base_sha = _committed_repository(tmp_path)
    manager = WorkspaceManager(tmp_path / ".workspaces")

    base = manager.materialize(repository, base_sha, "job-1")
    base_hash = _content_hash(base / "app.py")
    assert read_text(base / "app.py") == "first line\nsecond line\n"

    candidate = manager.create_candidate("job-1", 1)
    write_text(candidate / "app.py", "candidate content\r\n")
    second_candidate = manager.create_candidate("job-1", 2)

    assert _content_hash(base / "app.py") == base_hash
    assert read_text(candidate / "app.py") == "candidate content\n"
    assert _content_hash(second_candidate / "app.py") == base_hash

    manager.cleanup_candidate(candidate)
    manager.cleanup_candidate(second_candidate)
    assert not candidate.exists()
    assert not second_candidate.exists()
    assert base.is_dir()


def test_existing_base_and_candidate_are_never_reused(tmp_path: Path) -> None:
    repository, base_sha = _committed_repository(tmp_path)
    manager = WorkspaceManager(tmp_path / ".workspaces")
    manager.materialize(repository, base_sha, "job-2")
    manager.create_candidate("job-2", 1)

    with pytest.raises(WorkspaceExistsError):
        manager.materialize(repository, base_sha, "job-2")
    with pytest.raises(WorkspaceExistsError):
        manager.create_candidate("job-2", 1)


def test_apply_changes_normalizes_content_and_rejects_path_escape(
    tmp_path: Path,
) -> None:
    repository, base_sha = _committed_repository(tmp_path)
    manager = WorkspaceManager(tmp_path / ".workspaces")
    base = manager.materialize(repository, base_sha, "job-apply")
    base_hash = _content_hash(base / "app.py")

    candidate = manager.apply_changes(
        "job-apply",
        1,
        {"app.py": "candidate\r\ncontent\r"},
    )

    assert read_text(candidate / "app.py") == "candidate\ncontent\n"
    assert _content_hash(base / "app.py") == base_hash

    with pytest.raises(WorkspaceError, match="unsafe patch path"):
        manager.apply_changes("job-apply", 2, {"../outside.py": "blocked"})

    assert not (tmp_path / "outside.py").exists()
    assert not (manager.root / "job-apply" / "candidate-2").exists()


def test_cleanup_refuses_base_and_paths_outside_workspace(tmp_path: Path) -> None:
    manager = WorkspaceManager(tmp_path / ".workspaces")
    outside = tmp_path / "candidate-1"
    outside.mkdir()

    with pytest.raises(WorkspaceError):
        manager.cleanup_candidate(outside)
    with pytest.raises(WorkspaceError):
        manager.cleanup_candidate(manager.root / "job-1" / "base")

    assert outside.is_dir()


def test_readonly_cleanup_recovery_removes_the_blocked_path(tmp_path: Path) -> None:
    blocked = tmp_path / "readonly.txt"
    write_text(blocked, "temporary\n")
    blocked.chmod(0o444)

    _remove_readonly(os.unlink, str(blocked), None)

    assert not blocked.exists()
