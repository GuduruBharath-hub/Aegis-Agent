from __future__ import annotations

import asyncio

import pytest

from backend.agent.llm_client import (
    BehaviourPreservation,
    LineRationale,
    ModelTechnicalError,
    PatchFile,
    PatchModelError,
    PatchProposal,
    PatchRationale,
    RejectedAlternative,
)
from backend.agent.model_router import AllModelsUnavailableError, ModelRouter
from backend.core.config import ModelChainError, ModelSlot, load_model_chain
from backend.core.models import Finding

FINDING = Finding(
    id="AEGIS-89-001",
    scanner="aegis-ast",
    rule_id="AEGIS-SQL-CONCAT",
    category="SQL_INJECTION",
    cwe="CWE-89",
    severity="HIGH",
    confidence="HIGH",
    file_path="app/database.py",
    line_start=48,
    line_end=49,
    symbol="search_users",
    message="Query built by concatenation",
)


def _proposal(path: str = "app/database.py") -> PatchProposal:
    return PatchProposal(
        summary="Bind the search term",
        strategy="parameterized_query",
        files=(PatchFile(path=path, new_content="print('x')\n"),),
        injection_observed=False,
        rationale=PatchRationale(
            vulnerability_mechanism=(
                "Caller-controlled input becomes executable SQL syntax in this query."
            ),
            fix_mechanism=(
                "A driver-managed binding keeps caller input outside the SQL grammar."
            ),
            line_rationales=(
                LineRationale(
                    path=path,
                    changed_lines=(1,),
                    change_kind="parameterize",
                    why=(
                        "The query text no longer carries caller-controlled data, so "
                        "the term cannot be parsed as SQL."
                    ),
                    earns="security.payload[0]",
                ),
            ),
            behaviour_preservation=(
                BehaviourPreservation(
                    behaviour="substring matching on partial names",
                    preserved_by="wildcards moved inside the bound parameter",
                    proven_by="tests/test_users.py::test_search_partial_match",
                ),
            ),
            rejected_alternatives=(
                RejectedAlternative(
                    approach="strip quote characters from the input",
                    why_not="that breaks legitimate names such as O'Brien",
                ),
            ),
            residual_risk=("Other call sites require independent review.",),
            reviewer_must_confirm=("No other call site builds this query.",),
        ),
    )


class _Model:
    def __init__(self, name: str, *, fails: bool = False) -> None:
        self.name = name
        self._fails = fails
        self.calls = 0

    async def generate_patch(self, finding, **kwargs) -> PatchProposal:  # type: ignore[no-untyped-def]
        del finding, kwargs
        self.calls += 1
        if self._fails:
            raise PatchModelError(f"{self.name} is out of credit")
        return _proposal()


def test_router_fails_over_to_the_next_provider() -> None:
    dead = _Model("glm-5.3", fails=True)
    alive = _Model("deepseek-chat")
    router = ModelRouter((("primary", dead), ("fallback-1", alive)))

    proposal = asyncio.run(router.generate_patch(FINDING))

    assert proposal.summary == "Bind the search term"
    assert dead.calls == 1
    assert alive.calls == 1


def test_router_attributes_the_patch_to_the_provider_that_produced_it() -> None:
    """attempts.model must never credit a patch to a model that did not write it."""
    dead = _Model("glm-5.3", fails=True)
    alive = _Model("deepseek-chat")
    router = ModelRouter((("primary", dead), ("fallback-1", alive)))

    assert router.name == "glm-5.3"
    asyncio.run(router.generate_patch(FINDING))
    assert router.name == "deepseek-chat"


def test_router_does_not_call_later_providers_when_the_first_succeeds() -> None:
    first = _Model("glm-5.3")
    second = _Model("deepseek-chat")
    router = ModelRouter((("primary", first), ("fallback-1", second)))

    asyncio.run(router.generate_patch(FINDING))

    assert first.calls == 1
    assert second.calls == 0


def test_router_reports_each_failover_as_a_technical_error() -> None:
    reported: list[ModelTechnicalError] = []

    async def report(error: ModelTechnicalError) -> None:
        reported.append(error)

    router = ModelRouter(
        (("primary", _Model("glm-5.3", fails=True)), ("fallback-1", _Model("deepseek-chat")))
    )
    asyncio.run(router.generate_patch(FINDING, report_technical_error=report))

    assert len(reported) == 1
    assert reported[0].component == "model:primary"
    assert reported[0].code == "provider_unavailable"


def test_router_raises_when_every_provider_is_exhausted() -> None:
    router = ModelRouter(
        (
            ("primary", _Model("glm-5.3", fails=True)),
            ("fallback-1", _Model("deepseek-chat", fails=True)),
            ("fallback-2", _Model("qwen", fails=True)),
        )
    )

    with pytest.raises(AllModelsUnavailableError) as excinfo:
        asyncio.run(router.generate_patch(FINDING))

    assert len(excinfo.value.failures) == 3


def test_router_requires_at_least_one_model() -> None:
    with pytest.raises(ValueError):
        ModelRouter(())


def _slot_env(index: int, key: str, url: str, name: str) -> dict[str, str]:
    return {
        f"AEGIS_MODEL_{index}_API_KEY": key,
        f"AEGIS_MODEL_{index}_BASE_URL": url,
        f"AEGIS_MODEL_{index}_NAME": name,
    }


def test_chain_loads_three_slots_in_order() -> None:
    env = {
        **_slot_env(1, "k1", "https://one.example/v1", "glm-5.3"),
        **_slot_env(2, "k2", "https://two.example/v1", "deepseek-chat"),
        **_slot_env(3, "k3", "https://three.example/v1", "qwen"),
    }

    chain = load_model_chain(env)

    assert [slot.model for slot in chain] == ["glm-5.3", "deepseek-chat", "qwen"]
    assert [slot.label for slot in chain] == ["primary", "fallback-1", "fallback-2"]


def test_half_configured_slot_is_skipped_not_half_used() -> None:
    """A slot missing its key must be dropped at load time, not fail mid-demo."""
    env = {
        **_slot_env(1, "k1", "https://one.example/v1", "glm-5.3"),
        "AEGIS_MODEL_2_BASE_URL": "https://two.example/v1",
        "AEGIS_MODEL_2_NAME": "deepseek-chat",
    }

    chain = load_model_chain(env)

    assert len(chain) == 1
    assert chain[0].model == "glm-5.3"


def test_legacy_feather_names_still_populate_slot_one() -> None:
    env = {
        "FEATHER_API_KEY": "legacy",
        "FEATHER_BASE_URL": "https://api.featherless.ai/v1",
        "AEGIS_MODEL": "moonshotai/Kimi-K3",
    }

    chain = load_model_chain(env)

    assert len(chain) == 1
    assert chain[0].model == "moonshotai/Kimi-K3"
    assert chain[0].api_key.get_secret_value() == "legacy"


def test_missing_configuration_raises_a_named_error() -> None:
    with pytest.raises(ModelChainError):
        load_model_chain({})


def test_slot_api_key_is_not_exposed_by_repr() -> None:
    """Slots are logged during preflight; the key must not ride along."""
    slot = load_model_chain(_slot_env(1, "super-secret", "https://one.example/v1", "glm"))[0]

    assert "super-secret" not in repr(slot)
    assert isinstance(slot, ModelSlot)
