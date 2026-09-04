from __future__ import annotations

from backend.agent.feather_client import FeatherPatchModel
from backend.agent.llm_client import (
    ModelTechnicalError,
    PatchModelError,
    PatchProposal,
    TechnicalErrorReporter,
)
from backend.core.config import ModelSlot
from backend.core.models import FailureEvidence, Finding


class AllModelsUnavailableError(PatchModelError):
    """Every configured provider refused or failed."""

    def __init__(self, failures: tuple[tuple[str, str], ...]) -> None:
        detail = "; ".join(f"{label}: {reason}" for label, reason in failures)
        super().__init__(f"all configured models failed ({detail})")
        self.failures = failures


class ModelRouter:
    """Ordered provider chain with failover.

    Failover covers **transport**, not judgement. A provider that is rate
    limited, out of credit, unreachable, or returning unusable output is a
    delivery problem, and trying the next provider is the right response. A
    candidate that is *rejected by a gate* is not a failure of the provider —
    it is the system working — so it never triggers failover. It feeds
    self-correction, and the retry stays with the same brain that produced the
    rejected patch, because the retry prompt is addressed to that patch.

    Which provider actually produced a candidate is recorded per attempt, so
    the evidence trail never attributes a patch to the wrong model.
    """

    def __init__(self, models: tuple[tuple[str, object], ...]) -> None:
        if not models:
            raise ValueError("ModelRouter needs at least one model")
        self._models = models
        self.name = models[0][1].name  # type: ignore[attr-defined]
        self.chain = tuple(label for label, _ in models)

    @classmethod
    def from_slots(cls, slots: tuple[ModelSlot, ...], **kwargs: object) -> "ModelRouter":
        return cls(
            tuple(
                (slot.label, FeatherPatchModel(slot, **kwargs))  # type: ignore[arg-type]
                for slot in slots
            )
        )

    def describe(self) -> str:
        return " -> ".join(
            f"{label}:{model.name}"  # type: ignore[attr-defined]
            for label, model in self._models
        )

    async def generate_patch(
        self,
        finding: Finding,
        context: str = "",
        policy_summary: str = "",
        failure_evidence: FailureEvidence | None = None,
        report_technical_error: TechnicalErrorReporter | None = None,
    ) -> PatchProposal:
        failures: list[tuple[str, str]] = []
        total = len(self._models)

        for position, (label, model) in enumerate(self._models, start=1):
            try:
                proposal = await model.generate_patch(  # type: ignore[attr-defined]
                    finding,
                    context=context,
                    policy_summary=policy_summary,
                    failure_evidence=failure_evidence,
                    report_technical_error=report_technical_error,
                )
            except PatchModelError as exc:
                failures.append((label, exc.__class__.__name__))
                if report_technical_error is not None:
                    await report_technical_error(
                        ModelTechnicalError(
                            component=f"model:{label}",
                            code="provider_unavailable",
                            message=(
                                f"{label} ({model.name}) failed; "  # type: ignore[attr-defined]
                                + (
                                    f"failing over to {self._models[position][0]}"
                                    if position < total
                                    else "no provider left in the chain"
                                )
                            ),
                            request_number=position,
                            max_requests=total,
                        )
                    )
                continue

            # Attribute the candidate to the provider that actually produced it.
            self.name = model.name  # type: ignore[attr-defined]
            return proposal

        raise AllModelsUnavailableError(tuple(failures))
