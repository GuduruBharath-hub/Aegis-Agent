from __future__ import annotations

from pathlib import Path

from backend.agent.llm_client import (
    BehaviourPreservation,
    LineRationale,
    PatchRationale,
    RejectedAlternative,
)
from backend.core.workspace import write_text
from backend.verification import explain
from backend.verification.explain import changed_lines, evaluate


PASSED_TEST = "tests/test_app.py::test_search_partial_match"
EVIDENCE_REF = "security.payload[2]"


def _trees(tmp_path: Path) -> tuple[Path, Path, tuple[int, ...]]:
    base = tmp_path / "base"
    candidate = tmp_path / "candidate"
    write_text(
        base / "app.py",
        "def search(term, connection):\n"
        "    query = \"SELECT * FROM users WHERE name LIKE '%\" + term + \"%'\"\n"
        "    return connection.execute(query).fetchall()\n",
    )
    write_text(
        candidate / "app.py",
        "def search(term, connection):\n"
        "    query = \"SELECT * FROM users WHERE name LIKE ?\"\n"
        "    return connection.execute(query, (f\"%{term}%\",)).fetchall()\n",
    )
    lines = tuple(
        line for path, line in sorted(changed_lines(base, candidate)) if path == "app.py"
    )
    return base, candidate, lines


def _rationale(lines: tuple[int, ...]) -> PatchRationale:
    return PatchRationale(
        vulnerability_mechanism=(
            "The function concatenates caller input into SQL text before execution."
        ),
        fix_mechanism=(
            "The database driver binds the caller value separately from SQL syntax."
        ),
        line_rationales=(
            LineRationale(
                path="app.py",
                changed_lines=lines,
                change_kind="parameterize",
                why=(
                    "Separating query structure from the caller value prevents that "
                    "value from being interpreted as executable SQL syntax."
                ),
                earns=EVIDENCE_REF,
            ),
        ),
        behaviour_preservation=(
            BehaviourPreservation(
                behaviour="partial-name matching",
                preserved_by="wildcards remain inside the bound value",
                proven_by=PASSED_TEST,
            ),
        ),
        rejected_alternatives=(
            RejectedAlternative(
                approach="strip quotes",
                why_not="legitimate apostrophes would stop matching",
            ),
        ),
        residual_risk=("Only configured payloads were exercised.",),
        reviewer_must_confirm=("Review other SQL call sites manually.",),
    )


def _evaluate(base: Path, candidate: Path, rationale: PatchRationale):
    return evaluate(
        base,
        candidate,
        rationale,
        passed_test_ids=(PASSED_TEST,),
        evidence_refs=(EVIDENCE_REF,),
    )


def test_complete_anchored_rationale_passes(tmp_path: Path) -> None:
    base, candidate, lines = _trees(tmp_path)

    result = _evaluate(base, candidate, _rationale(lines))

    assert result.passed is True
    assert result.violations == ()


def test_unexplained_changed_line_fails(tmp_path: Path) -> None:
    base, candidate, lines = _trees(tmp_path)
    rationale = _rationale(lines).model_copy(
        update={
            "line_rationales": (
                _rationale(lines).line_rationales[0].model_copy(
                    update={"changed_lines": lines[:-1]}
                ),
            )
        }
    )

    result = _evaluate(base, candidate, rationale)

    assert "unexplained_lines" in {item.code for item in result.violations}


def test_rationale_for_unchanged_line_fails(tmp_path: Path) -> None:
    base, candidate, lines = _trees(tmp_path)
    rationale = _rationale(lines).model_copy(
        update={
            "line_rationales": (
                _rationale(lines).line_rationales[0].model_copy(
                    update={"changed_lines": (*lines, 99)}
                ),
            )
        }
    )

    result = _evaluate(base, candidate, rationale)

    assert "rationale_for_unchanged_line" in {
        item.code for item in result.violations
    }


def test_fabricated_test_citation_fails(tmp_path: Path) -> None:
    base, candidate, lines = _trees(tmp_path)
    fake_claim = _rationale(lines).behaviour_preservation[0].model_copy(
        update={"proven_by": "tests/test_app.py::test_does_not_exist"}
    )
    rationale = _rationale(lines).model_copy(
        update={"behaviour_preservation": (fake_claim,)}
    )

    result = _evaluate(base, candidate, rationale)

    assert result.passed is False
    assert [item.code for item in result.violations] == ["uncitable_test"]


def test_dangling_security_evidence_reference_fails(tmp_path: Path) -> None:
    base, candidate, lines = _trees(tmp_path)
    line_rationale = _rationale(lines).line_rationales[0].model_copy(
        update={"earns": "security.payload[999]"}
    )
    rationale = _rationale(lines).model_copy(
        update={"line_rationales": (line_rationale,)}
    )

    result = _evaluate(base, candidate, rationale)

    assert "dangling_evidence_ref" in {item.code for item in result.violations}


def test_restatement_without_reasoning_fails(tmp_path: Path) -> None:
    base, candidate, lines = _trees(tmp_path)
    line_rationale = _rationale(lines).line_rationales[0].model_copy(
        update={"why": "This line binds the parameter."}
    )
    rationale = _rationale(lines).model_copy(
        update={"line_rationales": (line_rationale,)}
    )

    result = _evaluate(base, candidate, rationale)

    assert "restatement_not_reasoning" in {
        item.code for item in result.violations
    }


def test_empty_reviewer_checklist_fails(tmp_path: Path) -> None:
    base, candidate, lines = _trees(tmp_path)
    rationale = _rationale(lines).model_copy(update={"reviewer_must_confirm": ()})

    result = _evaluate(base, candidate, rationale)

    assert "empty_reviewer_checklist" in {
        item.code for item in result.violations
    }


def test_parametrised_test_may_be_cited_by_its_function_id() -> None:
    """Pytest reports `f[1-Alice]`; a model reading the source sees only `f`.

    Demanding the instance id rejects a correct citation of a real, passing
    test. A false rejection damages this project's claim exactly as much as a
    false verification.
    """
    citable = explain._citable_test_ids(
        (
            "tests/test_database.py::test_get_user[1-Alice]",
            "tests/test_database.py::test_get_user[2-Bob]",
            "tests/test_database.py::test_plain",
        ),
        (),
    )

    assert "tests/test_database.py::test_get_user" in citable
    assert "tests/test_database.py::test_get_user[1-Alice]" in citable
    assert "tests/test_database.py::test_plain" in citable


def test_function_id_is_not_citable_when_any_case_failed() -> None:
    """If one parametrised case failed, the function as a whole did not hold."""
    citable = explain._citable_test_ids(
        ("tests/test_database.py::test_get_user[1-Alice]",),
        ("tests/test_database.py::test_get_user[2-Bob]",),
    )

    assert "tests/test_database.py::test_get_user" not in citable
    assert "tests/test_database.py::test_get_user[1-Alice]" in citable


def test_fabricated_citation_is_still_rejected() -> None:
    """The relaxation must not weaken the check that matters most."""
    citable = explain._citable_test_ids(
        ("tests/test_database.py::test_get_user[1-Alice]",), ()
    )

    assert "tests/test_database.py::test_invented_by_the_model" not in citable
