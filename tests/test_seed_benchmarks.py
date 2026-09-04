import json
from pathlib import Path

from backend.core.workspace import write_text
from scripts.seed_benchmarks import seed_benchmark_repositories


def test_seed_benchmarks_creates_reproducible_git_fixture(tmp_path: Path) -> None:
    fixture = tmp_path / "benchmarks" / "case-one"
    write_text(fixture / "app.py", "value = 1\n")
    write_text(
        tmp_path / "benchmarks" / "MANIFEST.json",
        json.dumps({"cases": [{"id": "case-one"}]}),
    )

    assert seed_benchmark_repositories(tmp_path) == ("case-one",)
    assert (fixture / ".git").is_dir()
    assert seed_benchmark_repositories(tmp_path) == ()
